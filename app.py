#!/usr/bin/env python3
"""Local resume editor for the supplied Jake-style LaTeX resume.

No Python third-party dependencies are required. A browser is used as the GUI,
and pdflatex is used to compile the generated LaTeX into a PDF.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DATA_FILE = DATA_DIR / "resume.json"
TEX_TEMPLATE = ROOT / "template.tex"
TEX_OUT = OUTPUT_DIR / "resume.tex"
PDF_OUT = OUTPUT_DIR / "resume.pdf"
PORT = 8765

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def load_resume() -> dict:
    if not DATA_FILE.exists():
        return default_resume()
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return default_resume()


def save_resume(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_resume() -> dict:
    return {
        "section_order": ["summary", "skills", "experience", "education"],
        "personal": {
            "name": "Subho Chowdhury",
            "location": "Kolkata, West Bengal 700156",
            "phone": "+91 8250016128",
            "email": "subhochowdhury50@gmail.com",
            "linkedin_url": "https://linkedin.com/in/subho-chowdhury-24439b170",
            "linkedin_text": "www.linkedin.com/in/subho-chowdhury-24439b170",
        },
        "summary": "Java Backend Engineer with 5 years of experience in microservices and event-driven systems. Skilled in Java, Spring Boot, Kafka, and AWS, with proven success in building real-time pipelines, PostgreSQL and Elasticsearch integrations, and improving observability across distributed systems.",
        "skills": [
            {"category": "Languages", "items": "Java (JDK 17), Python, SQL (PostgreSQL), Bash"},
            {"category": "Frameworks", "items": "Spring Boot, Spring Security, Spring Data JPA"},
            {"category": "Developer Tools", "items": "Git, Docker, IntelliJ, Java Flight Recorder, Heap Dump Analysis"},
            {"category": "Testing & QA", "items": "JUnit 5, Mockito, Testcontainers, JMeter, Load Testing, Integration Testing"},
            {"category": "CI/CD", "items": "Maven, GitHub Actions"},
            {"category": "Messaging & Streaming", "items": "Apache Zookeeper, Apache Kafka, Kafka Streams, Kafka Connect, AWS SNS, AWS SQS"},
            {"category": "Databases", "items": "PostgreSQL, DynamoDB, Redis"},
            {"category": "Cloud & Infrastructure", "items": "AWS (S3, IAM, Lambda, EventBridge, EC2, CloudWatch), Docker Compose"},
            {"category": "Architecture & Patterns", "items": "REST APIs, Microservices, Event-Driven Architecture, Change Data Capture, Audit Logging, Design Patterns"},
            {"category": "Observability & Logging", "items": "OpenTelemetry, Prometheus, Grafana, ELK Stack, SLF4J, Logback"},
        ],
        "experience": [
            {
                "company": "Tata Consultancy Services",
                "dates": "August 2023 - Present",
                "role": "IT Analyst",
                "location": "Kolkata, West Bengal",
                "bullets": [
                    "Designed and deployed an internal document processing platform handling 5,000+ scanned PDFs/images daily, using AWS Textract for OCR, Kafka for inter-service messaging and AWS S3 + Lambda + EventBridge for asynchronous processing. Reduced manual processing time by 80%",
                    "Replaced SQL text search with Elasticsearch, and built a CDC pipeline (Debezium + Kafka Connect + Kafka Streams) syncing 2M+ records from PostgreSQL in near real-time (<5 min). Improved search latency by 70% and made results more relevant.",
                    "Implemented distributed tracing and observability across 10+ microservices using OpenTelemetry + Prometheus + Grafana. Enabled request-level monitoring of latency, errors and bottlenecks, leading to faster bug discovery time during integration and 20% decrease in staging environment failures.",
                    "Mentored 3 interns on AI/ML projects, one of them later joined full-time. Additionally helped onboard and support freshers by reviewing their code, explaining project designs, and helping them to be productive contributors.",
                ],
            },
            {
                "company": "Tata Consultancy Services",
                "dates": "August 2020 - August 2023",
                "role": "System Engineer",
                "location": "Kolkata, West Bengal",
                "bullets": [
                    "Built an event-driven feedback routing system with Kafka + AWS Lambda + EventBridge, integrating lightweight NLP models for dynamic classification. Automated manual routing, saving 60% effort while maintaining 90%+ accuracy.",
                    "Increased test coverage by 80% by writing JUnit5 + Mockito + Testcontainers tests and built load-testing scripts in JMeter to simulate production traffic and identify performance issues early.",
                    "Created an internal tool using Azure OpenAI + SonarQube API that converted static analysis warnings into plain English with suggested fixes. Improved onboarding and reduced confusion for new developers dealing with code quality issues.",
                ],
            },
        ],
        "education": [
            {
                "institution": "MAKAUT",
                "dates": "Aug. 2016 -- Aug 2020",
                "degree": "Bachelor of Technology in Computer Science",
                "location": "Asansol, West Bengal",
            }
        ],
    }


def latex_escape(value: object) -> str:
    """Escape text for safe insertion into regular LaTeX text."""
    s = "" if value is None else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in s)


def latex_href(value: object) -> str:
    """Escape URL-ish text for use inside hyperref's href argument."""
    s = "" if value is None else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "#": r"\#",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        " ": "%20",
    }
    return "".join(replacements.get(ch, ch) for ch in s)


def clean_data(data: dict) -> dict:
    """Normalize user-submitted JSON and cap pathological sizes."""
    data = data if isinstance(data, dict) else {}
    personal = data.get("personal") or {}
    allowed_sections = ("summary", "skills", "experience", "education")
    requested_order = data.get("section_order") or []
    section_order = []
    if isinstance(requested_order, list):
        for key in requested_order:
            if key in allowed_sections and key not in section_order:
                section_order.append(key)
    section_order.extend(key for key in allowed_sections if key not in section_order)

    out = {
        "section_order": section_order,
        "personal": {
            "name": str(personal.get("name", ""))[:120],
            "location": str(personal.get("location", ""))[:160],
            "phone": str(personal.get("phone", ""))[:80],
            "email": str(personal.get("email", ""))[:160],
            "linkedin_url": str(personal.get("linkedin_url", ""))[:300],
            "linkedin_text": str(personal.get("linkedin_text", ""))[:180],
        },
        "summary": str(data.get("summary", ""))[:1800],
        "skills": [],
        "experience": [],
        "education": [],
    }
    for skill in (data.get("skills") or [])[:20]:
        if not isinstance(skill, dict):
            continue
        out["skills"].append({
            "category": str(skill.get("category", ""))[:100],
            "items": str(skill.get("items", ""))[:600],
        })
    for exp in (data.get("experience") or [])[:20]:
        if not isinstance(exp, dict):
            continue
        out["experience"].append({
            "company": str(exp.get("company", ""))[:150],
            "dates": str(exp.get("dates", ""))[:100],
            "role": str(exp.get("role", ""))[:160],
            "location": str(exp.get("location", ""))[:160],
            "bullets": [str(b)[:1200] for b in (exp.get("bullets") or [])[:12]],
        })
    for edu in (data.get("education") or [])[:12]:
        if not isinstance(edu, dict):
            continue
        out["education"].append({
            "institution": str(edu.get("institution", ""))[:150],
            "dates": str(edu.get("dates", ""))[:100],
            "degree": str(edu.get("degree", ""))[:180],
            "location": str(edu.get("location", ""))[:160],
        })
    return out


def render_summary(data: dict) -> str:
    return r"\section{Professional Summary}" + "\n    " + latex_escape(data.get("summary", "")) + "\n"


def render_skills(data: dict) -> str:
    pieces = [r"""%-----------PROGRAMMING SKILLS-----------
\section{Technical Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
"""]
    for skill in data["skills"]:
        if skill["category"].strip() or skill["items"].strip():
            pieces.append(
                r"     \textbf{" + latex_escape(skill["category"])
                + r"}{: " + latex_escape(skill["items"]) + r"} " + r"\\" + "\n"
            )
    pieces.append(r"""    }}
 \end{itemize}
 
 \vspace{-16pt}
""")
    return "".join(pieces)


def render_experience(data: dict) -> str:
    pieces = [r"%-----------EXPERIENCE-----------" + "\n" + r"\section{Experience}" + "\n"]
    for exp in data["experience"]:
        pieces.append("  \\resumeSubHeadingListStart\n")
        pieces.append(
            "    \\resumeSubheading\n      {%s}{%s}\n      {%s}{%s}\n"
            % (
                latex_escape(exp["company"]),
                latex_escape(exp["dates"]),
                latex_escape(exp["role"]),
                latex_escape(exp["location"]),
            )
        )
        pieces.append("      \\resumeItemListStart\n")
        for bi, bullet in enumerate(exp["bullets"]):
            pieces.append("      \\vspace{4pt}\n" if bi == 0 else "        \\vspace{4pt}\n")
            if bullet.strip():
                pieces.append("        \\resumeItem{%s}\n" % latex_escape(bullet))
        pieces.append("      \\resumeItemListEnd\n")
        pieces.append("  \\resumeSubHeadingListEnd\n\n")
    pieces.append("\\vspace{-16pt}\n\n")
    return "".join(pieces)


def render_education(data: dict) -> str:
    pieces = [r"%-----------EDUCATION-----------" + "\n" + r"\section{Education}" + "\n  " + r"\resumeSubHeadingListStart" + "\n"]
    for edu in data["education"]:
        pieces.append(
            "    \\resumeSubheading\n      {%s}{%s}\n      {%s}{%s}\n"
            % (
                latex_escape(edu["institution"]),
                latex_escape(edu["dates"]),
                latex_escape(edu["degree"]),
                latex_escape(edu["location"]),
            )
        )
    pieces.append("  \\resumeSubHeadingListEnd\n")
    return "".join(pieces)


def render_body(data: dict) -> str:
    p = data["personal"]
    pieces = []
    header_lines = [
    r"%----------HEADING----------",
    r"\begin{center}",
    r"    {\Huge \scshape " + latex_escape(p.get("name", "")) + r"} \\ \vspace{1pt}",
    "    " + latex_escape(p.get("location", "")) + r" \\ \vspace{1pt}",
    r"    \small "
    + latex_escape(p.get("phone", ""))
    + r" \textbar\ "
    + r"\href{mailto:" + latex_href(p.get("email", "")) + r"}{\underline{"
    + latex_escape(p.get("email", "")) + r"}} ~ \textbar\ ",
]
    if p.get("linkedin_url") and p.get("linkedin_text"):
        header_lines.append(
            r"    \href{" + latex_href(p.get("linkedin_url", "")) + r"}{\underline{"
            + latex_escape(p.get("linkedin_text", "")) + r"}}"
        )
    header_lines.append(r"\end{center}")
    pieces.append("\n".join(header_lines) + "\n")

    renderers = {
        "summary": render_summary,
        "skills": render_skills,
        "experience": render_experience,
        "education": render_education,
    }
    for section in data.get("section_order", ["summary", "skills", "experience", "education"]):
        renderer = renderers.get(section)
        if renderer:
            pieces.append(renderer(data))
    return "".join(pieces)


def render_tex(data: dict) -> str:
    template = TEX_TEMPLATE.read_text(encoding="utf-8")
    return template.replace("%%RESUME_BODY%%", render_body(data))


def compile_pdf(tex_text: str) -> tuple[bool, str]:
    TEX_OUT.write_text(tex_text, encoding="utf-8")
    build_dir = OUTPUT_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    local_tex = build_dir / "resume.tex"
    local_tex.write_text(tex_text, encoding="utf-8")

    cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "resume.tex"]
    logs = []
    for _ in range(2):
        try:
            proc = subprocess.run(cmd, cwd=build_dir, capture_output=True, text=True, timeout=45)
        except FileNotFoundError:
            return False, "pdflatex was not found. Install a LaTeX distribution (e.g. TeX Live) and try again."
        except subprocess.TimeoutExpired:
            return False, "LaTeX compilation timed out after 45 seconds."
        logs.append(proc.stdout + "\n" + proc.stderr)
        if proc.returncode != 0:
            return False, extract_latex_error(logs[-1])

    generated_pdf = build_dir / "resume.pdf"
    if not generated_pdf.exists():
        return False, "pdflatex completed but no PDF was produced."
    shutil.copy2(generated_pdf, PDF_OUT)
    return True, "PDF generated successfully."


def extract_latex_error(log: str) -> str:
    lines = log.splitlines()
    errors = [ln.strip() for ln in lines if ln.startswith("!")]
    if errors:
        return errors[-1]
    for ln in lines:
        if "LaTeX Error:" in ln:
            return ln.strip()
    for ln in reversed(lines):
        if ln.strip() and "Transcript written on" not in ln:
            return ln.strip()
    return "LaTeX compilation failed."


class Handler(BaseHTTPRequestHandler):
    server_version = "ResumeBuilder/1.0"

    def _json(self, payload: dict, status: int = 200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, content_type: str, download: bool = False):
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/api/resume":
            self._json(load_resume())
        elif path == "/api/status":
            self._json({"pdflatex": shutil.which("pdflatex") is not None, "pdf": PDF_OUT.exists(), "tex": TEX_OUT.exists()})
        elif path == "/resume.pdf":
            self._send_file(PDF_OUT, "application/pdf")
        elif path == "/download/resume.pdf":
            self._send_file(PDF_OUT, "application/pdf", download=True)
        elif path == "/download/resume.tex":
            self._send_file(TEX_OUT, "application/x-tex; charset=utf-8", download=True)
        elif path.startswith("/static/"):
            relative = path[len("/static/"):]
            target = (STATIC_DIR / relative).resolve()
            if STATIC_DIR.resolve() not in target.parents:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_types = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".html": "text/html; charset=utf-8"}
            self._send_file(target, content_types.get(target.suffix, "application/octet-stream"))
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        if length > 2_000_000:
            self._json({"ok": False, "message": "Request too large."}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._json({"ok": False, "message": "Invalid JSON."}, HTTPStatus.BAD_REQUEST)
            return

        if path in ("/api/save", "/api/generate"):
            data = clean_data(payload)
            save_resume(data)
            tex_text = render_tex(data)
            if path == "/api/save":
                self._json({"ok": True, "message": "Resume saved."})
                return
            ok, message = compile_pdf(tex_text)
            self._json({
                "ok": ok,
                "message": message,
                "pdf_url": "/resume.pdf?ts=" + str(int(__import__("time").time())),
                "tex_url": "/download/resume.tex",
            }, HTTPStatus.OK if ok else HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args):
        # Keep console output useful but quiet.
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    if not DATA_FILE.exists():
        save_resume(default_resume())
    # Generate initial files so the preview is immediately available.
    data = load_resume()
    ok, message = compile_pdf(render_tex(data))
    if not ok:
        print("Initial PDF generation warning:", message)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Resume Builder running at {url}")
    print("Press Ctrl+C to stop.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Resume Builder...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
