from flask import Flask, request, Response, render_template_string
import json
import os
from google import genai

API_KEY = os.environ.get("KEY")
if not API_KEY:
    raise SystemExit(
        "Missing API key. Set the KEY environment variable first, e.g.\n"
        "  Windows (cmd):        set KEY=your_actual_key\n"
        "  Windows (PowerShell): $env:KEY=\"your_actual_key\"\n"
        "  Mac/Linux:            export KEY=your_actual_key"
    )
MODEL = "gemini-3.5-flash-lite"

TOPIC = "History"
NUM_Q = 5
DIFF = "intermediate"
LANG = "English"

PROMPT = """
Generate a quiz according to the following specifications:

- topic: {topic}
- num_q: {num_q}
- diff: {diff}
- lang: {lang}

Output should be (only) an unquoted JSON array of objects with keys "question", "responses", and "correct".
"responses" must be an array of answer strings, and "correct" must be exactly equal to one of the strings in "responses".
"""

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8080))
client = genai.Client(api_key=API_KEY)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Quiz Generator</title>
    <style>
        :root {
            --purple: #6c5ce7;
            --purple-dark: #5446d6;
            --blue: #4c8df6;
            --green: #1fa971;
            --green-bg: #e3f8ee;
            --red: #e5484d;
            --red-bg: #fdeaea;
            --ink: #1f2340;
            --muted: #6b7194;
            --line: #e6e8f5;
            --soft: #f6f7ff;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            font-family: "Segoe UI", system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif;
            color: var(--ink);
            background: linear-gradient(135deg, #6c5ce7 0%, #4c8df6 55%, #38bdf8 100%) fixed;
            padding: 40px 16px 60px;
        }
        .wrap { max-width: 760px; margin: 0 auto; }

        header { text-align: center; color: white; margin-bottom: 24px; }
        header .logo { font-size: 44px; line-height: 1; margin-bottom: 8px; }
        header h1 { margin: 0; font-size: 34px; letter-spacing: -0.5px; }
        header p { margin: 8px 0 0; opacity: 0.9; font-size: 16px; }

        .card {
            background: white;
            border-radius: 22px;
            padding: 28px;
            box-shadow: 0 20px 50px rgba(20, 20, 70, 0.25);
        }

        /* ---------- setup form ---------- */
        .setup {
            display: grid;
            grid-template-columns: 1fr 100px 150px;
            gap: 14px;
            align-items: end;
            padding-bottom: 24px;
            margin-bottom: 24px;
            border-bottom: 1px solid var(--line);
        }
        .field label { display: block; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: var(--muted); margin-bottom: 6px; cursor: default; padding: 0; }
        .field label:hover { background: none; }
        .field input, .field select {
            width: 100%;
            padding: 12px 14px;
            font-size: 15px;
            font-family: inherit;
            color: var(--ink);
            border: 2px solid var(--line);
            border-radius: 12px;
            background: var(--soft);
            outline: none;
            transition: border-color 0.15s, background 0.15s;
        }
        .field input:focus, .field select:focus { border-color: var(--purple); background: white; }
        .setup .go { grid-column: 1 / -1; }

        /* ---------- buttons ---------- */
        .btn {
            display: block;
            width: 100%;
            border: none;
            cursor: pointer;
            font-family: inherit;
            font-size: 16px;
            font-weight: 700;
            color: white;
            padding: 14px 20px;
            border-radius: 14px;
            background: linear-gradient(135deg, var(--purple), var(--blue));
            box-shadow: 0 8px 20px rgba(108, 92, 231, 0.35);
            transition: transform 0.12s, box-shadow 0.12s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 12px 26px rgba(108, 92, 231, 0.45); }
        .btn:active { transform: translateY(0); }
        .btn.secondary { background: white; color: var(--purple); border: 2px solid var(--purple); box-shadow: none; margin-top: 16px; }
        .btn.secondary:hover { background: var(--soft); }

        /* ---------- loading ---------- */
        .loading { text-align: center; padding: 40px 0; color: var(--muted); }
        .spinner {
            width: 42px; height: 42px; margin: 0 auto 14px;
            border: 4px solid var(--line);
            border-top-color: var(--purple);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .error { color: var(--red); background: var(--red-bg); padding: 14px 16px; border-radius: 12px; }

        /* ---------- progress ---------- */
        .progress {
            position: sticky; top: 0; z-index: 5;
            background: white;
            padding: 4px 0 16px;
            margin-bottom: 8px;
        }
        .progress-top { display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 8px; }
        .bar { height: 8px; border-radius: 99px; background: var(--line); overflow: hidden; }
        .bar > div { height: 100%; width: 0; border-radius: 99px; background: linear-gradient(90deg, var(--purple), var(--blue)); transition: width 0.25s ease; }

        /* ---------- questions ---------- */
        .question-block {
            background: var(--soft);
            border: 2px solid transparent;
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 16px;
            animation: rise 0.35s ease both;
        }
        @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
        .question-block.right { border-color: var(--green); background: #f4fcf8; }
        .question-block.wrong { border-color: var(--red); background: #fff7f7; }

        .q-head { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 12px; }
        .q-num {
            flex: none;
            width: 32px; height: 32px;
            display: grid; place-items: center;
            font-weight: 800; font-size: 14px; color: white;
            border-radius: 10px;
            background: linear-gradient(135deg, var(--purple), var(--blue));
        }
        .q-text { margin: 0; font-size: 17px; font-weight: 700; line-height: 1.4; padding-top: 3px; }

        .verdict {
            display: inline-block;
            font-weight: 700; font-size: 13px;
            padding: 5px 12px;
            border-radius: 99px;
            margin: 0 0 12px 44px;
        }
        .verdict.right { color: var(--green); background: var(--green-bg); }
        .verdict.wrong { color: var(--red); background: var(--red-bg); }

        .options { display: grid; gap: 10px; }
        label.option {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 0;
            padding: 12px 14px;
            background: white;
            border: 2px solid var(--line);
            border-radius: 12px;
            cursor: pointer;
            font-size: 15px;
            transition: border-color 0.15s, background 0.15s, transform 0.1s;
        }
        label.option:hover { border-color: #b9b3f5; background: #fbfaff; }
        label.option input { position: absolute; opacity: 0; pointer-events: none; }
        .letter {
            flex: none;
            width: 28px; height: 28px;
            display: grid; place-items: center;
            font-size: 13px; font-weight: 800;
            color: var(--muted);
            background: var(--soft);
            border-radius: 8px;
            transition: all 0.15s;
        }
        .opt-text { flex: 1; line-height: 1.35; }
        label.option.selected { border-color: var(--purple); background: #f3f1ff; }
        label.option.selected .letter { background: var(--purple); color: white; }

        /* graded states */
        label.option.locked { cursor: default; }
        label.option.locked:hover { background: white; border-color: var(--line); }
        label.option.picked-correct { background: var(--green-bg); border-color: var(--green); }
        label.option.picked-correct .letter { background: var(--green); color: white; }
        label.option.picked-correct::after { content: "✓ Your answer"; color: var(--green); font-weight: 700; font-size: 13px; }
        label.option.picked-wrong { background: var(--red-bg); border-color: var(--red); }
        label.option.picked-wrong .letter { background: var(--red); color: white; }
        label.option.picked-wrong::after { content: "✗ Your answer"; color: var(--red); font-weight: 700; font-size: 13px; }
        label.option.reveal-correct { background: #f1fbf6; border: 2px dashed var(--green); }
        label.option.reveal-correct .letter { background: var(--green); color: white; }
        label.option.reveal-correct::after { content: "✓ Correct answer"; color: var(--green); font-weight: 700; font-size: 13px; }

        /* ---------- results ---------- */
        #results { margin-top: 8px; }
        .result-card {
            text-align: center;
            padding: 26px 20px;
            border-radius: 18px;
            background: linear-gradient(135deg, #f3f1ff, #eaf3ff);
            animation: rise 0.4s ease both;
        }
        .ring {
            width: 140px; height: 140px;
            margin: 0 auto 16px;
            border-radius: 50%;
            display: grid; place-items: center;
        }
        .ring-inner {
            width: 108px; height: 108px;
            border-radius: 50%;
            background: white;
            display: grid; place-items: center;
            font-size: 30px; font-weight: 800;
        }
        .ring-inner small { display: block; font-size: 13px; font-weight: 600; color: var(--muted); margin-top: -4px; }
        .result-title { font-size: 22px; font-weight: 800; margin: 0 0 6px; }
        .result-sub { margin: 0; color: var(--muted); font-size: 15px; }
        .chips { display: flex; justify-content: center; gap: 10px; margin-top: 14px; }
        .chip { font-weight: 700; font-size: 14px; padding: 6px 14px; border-radius: 99px; }
        .chip.good { color: var(--green); background: var(--green-bg); }
        .chip.bad { color: var(--red); background: var(--red-bg); }

        @media (max-width: 560px) {
            .setup { grid-template-columns: 1fr 1fr; }
            .setup .field:first-child { grid-column: 1 / -1; }
            .card { padding: 20px; }
            header h1 { font-size: 28px; }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <header>
            <div class="logo">🧠</div>
            <h1>AI Quiz Generator</h1>
            <p>Pick a topic and let AI write the questions.</p>
        </header>

        <div class="card">
            <form class="setup" method="get" action="/">
                <div class="field">
                    <label for="topic">Topic</label>
                    <input id="topic" type="text" name="topic" placeholder="e.g. Space, Movies, Biology" value="{{ topic }}">
                </div>
                <div class="field">
                    <label for="num_q">Questions</label>
                    <input id="num_q" type="number" name="num_q" min="1" max="20" value="{{ num_q }}">
                </div>
                <div class="field">
                    <label for="diff">Difficulty</label>
                    <select id="diff" name="diff">
                        {% for d in ["easy", "intermediate", "hard"] %}
                        <option value="{{ d }}" {% if d == diff %}selected{% endif %}>{{ d|capitalize }}</option>
                        {% endfor %}
                    </select>
                </div>
                <input type="hidden" name="lang" value="{{ lang }}">
                <button class="btn go" type="submit">✨ Generate New Quiz</button>
            </form>

            <div id="progress" class="progress" style="display:none;">
                <div class="progress-top"><span id="progress-label">0 of 0 answered</span><span id="progress-topic"></span></div>
                <div class="bar"><div id="progress-fill"></div></div>
            </div>

            <div id="quiz-container">
                <div class="loading"><div class="spinner"></div>Generating your quiz...</div>
            </div>

            <button id="submit-btn" class="btn" style="display:none;" onclick="gradeQuiz()">Submit Quiz</button>
            <div id="results"></div>
        </div>
    </div>

    <script>
        let quizData = [];
        let graded = false;

        function escapeHtml(s) {
            return String(s)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        }

        function updateProgress() {
            const answered = quizData.filter((q, i) => document.querySelector(`input[name="q${i}"]:checked`)).length;
            document.getElementById('progress-label').textContent = `${answered} of ${quizData.length} answered`;
            document.getElementById('progress-fill').style.width = (quizData.length ? (answered / quizData.length) * 100 : 0) + '%';
        }

        async function loadQuiz() {
            const container = document.getElementById('quiz-container');
            try {
                const params = new URLSearchParams(window.location.search);
                const response = await fetch('/api/generate?' + params.toString());
                if (!response.ok) {
                    const text = await response.text();
                    throw new Error('Server error ' + response.status + ': ' + text);
                }
                quizData = await response.json();
                if (!Array.isArray(quizData)) throw new Error('Quiz was not in the expected format.');
            } catch (err) {
                container.innerHTML = '<p class="error">Could not load quiz: ' + escapeHtml(err.message) + '</p>';
                return;
            }

            let html = '';
            quizData.forEach((q, index) => {
                html += `<div class="question-block">
                    <div class="q-head">
                        <div class="q-num">${index + 1}</div>
                        <p class="q-text">${escapeHtml(q.question)}</p>
                    </div>
                    <div class="options">`;

                q.responses.forEach((resp, rIndex) => {
                    const letter = String.fromCharCode(65 + rIndex);
                    html += `<label class="option">
                        <input type="radio" name="q${index}" value="${escapeHtml(resp)}">
                        <span class="letter">${letter}</span>
                        <span class="opt-text">${escapeHtml(resp)}</span>
                    </label>`;
                });

                html += `</div></div>`;
            });
            container.innerHTML = html;

            container.addEventListener('change', (e) => {
                if (graded || e.target.type !== 'radio') return;
                const group = document.querySelectorAll(`input[name="${e.target.name}"]`);
                group.forEach(r => r.closest('label').classList.toggle('selected', r.checked));
                updateProgress();
            });

            document.getElementById('progress').style.display = 'block';
            updateProgress();
            document.getElementById('submit-btn').style.display = 'block';
        }

        function gradeQuiz() {
            graded = true;
            let score = 0;
            const blocks = document.querySelectorAll('.question-block');

            quizData.forEach((q, index) => {
                const block = blocks[index];
                const selected = document.querySelector(`input[name="q${index}"]:checked`);
                const labels = block.querySelectorAll('label.option');
                const correctText = String(q.correct).trim();
                const isRight = selected && selected.value.trim() === correctText;

                labels.forEach(label => {
                    const input = label.querySelector('input');
                    input.disabled = true;
                    label.classList.remove('selected');
                    label.classList.add('locked');
                    const isCorrectChoice = input.value.trim() === correctText;

                    if (input.checked && isCorrectChoice) {
                        label.classList.add('picked-correct');   // their pick, right -> green
                    } else if (input.checked) {
                        label.classList.add('picked-wrong');     // their pick, wrong -> red
                    } else if (isCorrectChoice) {
                        label.classList.add('reveal-correct');   // the answer they should have picked
                    }
                });

                const verdict = document.createElement('div');
                verdict.className = 'verdict';
                if (isRight) {
                    score++;
                    block.classList.add('right');
                    verdict.classList.add('right');
                    verdict.textContent = '✓ Correct';
                } else {
                    block.classList.add('wrong');
                    verdict.classList.add('wrong');
                    verdict.textContent = selected ? '✗ Incorrect' : '✗ Not answered';
                }
                block.insertBefore(verdict, block.querySelector('.options'));
            });

            const total = quizData.length;
            const wrong = total - score;
            const pct = total ? Math.round((score / total) * 100) : 0;
            const color = pct >= 70 ? 'var(--green)' : (pct >= 40 ? '#f0a500' : 'var(--red)');
            let title = 'Keep practicing!';
            if (pct === 100) title = 'Perfect score! 🎉';
            else if (pct >= 80) title = 'Great job! 🙌';
            else if (pct >= 60) title = 'Nice work! 👍';
            else if (pct >= 40) title = 'Not bad, keep going!';

            document.getElementById('results').innerHTML = `
                <div class="result-card">
                    <div class="ring" style="background: conic-gradient(${color} ${pct * 3.6}deg, #e6e8f5 0deg);">
                        <div class="ring-inner"><div>${score}/${total}<small>${pct}%</small></div></div>
                    </div>
                    <p class="result-title">${title}</p>
                    <p class="result-sub">Scroll up to review each question.</p>
                    <div class="chips">
                        <span class="chip good">✓ ${score} right</span>
                        <span class="chip bad">✗ ${wrong} wrong</span>
                    </div>
                    <button class="btn secondary" onclick="window.location.reload()">Try a new quiz on this topic</button>
                </div>`;

            document.getElementById('submit-btn').style.display = 'none';
            document.getElementById('progress').style.display = 'none';
            document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        loadQuiz();
    </script>
</body>
</html>
"""


def check(args, name, default):
    if name in args and args[name].strip():
        return args[name].strip()
    return default


@app.route("/", methods=["GET"])
def home():
    args = request.args.to_dict()
    return render_template_string(
        HTML_TEMPLATE,
        topic=check(args, "topic", TOPIC),
        num_q=check(args, "num_q", NUM_Q),
        diff=check(args, "diff", DIFF),
        lang=check(args, "lang", LANG),
    )


@app.route("/api/generate", methods=["GET"])
def generate():
    args = request.args.to_dict()
    topic = check(args, "topic", TOPIC)
    num_q = check(args, "num_q", NUM_Q)
    diff = check(args, "diff", DIFF)
    lang = check(args, "lang", LANG)

    prompt = PROMPT.format(topic=topic, num_q=num_q, diff=diff, lang=lang)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        json.loads(clean_text)  # make sure it's valid JSON before sending it on
        return Response(clean_text, mimetype="application/json")
    except Exception as e:
        print("Quiz generation failed:", e)
        return Response(str(e), status=500, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
