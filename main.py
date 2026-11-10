from flask import Flask, request, Response, render_template_string
import json
import os
from google import genai

API_KEY = "KEY"
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
        body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; background: #f4f7f6; color: #333; }
        .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1 { color: #2c3e50; text-align: center; margin-top: 0; }
        .setup { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 25px; }
        .setup input, .setup select { padding: 10px; font-size: 15px; border: 1px solid #ccc; border-radius: 5px; }
        .setup input[name="topic"] { flex: 1; min-width: 150px; }
        .setup input[name="num_q"] { width: 70px; }
        .setup button { width: auto; padding: 10px 20px; }
        .question-block { margin-bottom: 20px; border-bottom: 1px solid #eee; padding: 0 0 15px 10px; border-left: 5px solid transparent; }
        label { display: block; margin: 8px 0; cursor: pointer; padding: 8px; border-radius: 5px; transition: background 0.2s; }
        label:hover { background: #f0f4f8; }
        button { background: #3498db; color: white; border: none; padding: 12px 20px; font-size: 16px; border-radius: 5px; cursor: pointer; display: block; width: 100%; }
        button:hover { background: #2980b9; }
        #results { font-weight: bold; font-size: 18px; text-align: center; margin-top: 20px; }
        .question-block.right { border-left-color: #27ae60; }
        .question-block.wrong { border-left-color: #c0392b; }
        .verdict { font-weight: bold; font-size: 14px; margin: 4px 0 8px; }
        .verdict.right { color: #27ae60; }
        .verdict.wrong { color: #c0392b; }
        label.picked-correct { background: #d4f5df; border: 2px solid #27ae60; }
        label.picked-wrong { background: #fbdcd9; border: 2px solid #c0392b; }
        label.reveal-correct { background: #eefaf2; border: 2px dashed #27ae60; }
        #results .score { font-size: 28px; }
        #results .summary { font-size: 15px; font-weight: normal; margin-top: 6px; color: #555; }
        .error { color: #c0392b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>AI Quiz Generator</h1>

        <form class="setup" method="get" action="/">
            <input type="text" name="topic" placeholder="Topic" value="{{ topic }}">
            <input type="number" name="num_q" min="1" max="20" value="{{ num_q }}">
            <select name="diff">
                {% for d in ["easy", "intermediate", "hard"] %}
                <option value="{{ d }}" {% if d == diff %}selected{% endif %}>{{ d }}</option>
                {% endfor %}
            </select>
            <input type="hidden" name="lang" value="{{ lang }}">
            <button type="submit">New Quiz</button>
        </form>

        <div id="quiz-container">Loading your AI-generated quiz...</div>
        <button id="submit-btn" style="display:none;" onclick="gradeQuiz()">Submit Answers</button>
        <div id="results"></div>
    </div>

    <script>
        let quizData = [];

        function escapeHtml(s) {
            return String(s)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
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

            container.innerHTML = '';

            quizData.forEach((q, index) => {
                let html = `<div class="question-block">
                    <p><strong>Q${index + 1}: ${escapeHtml(q.question)}</strong></p>`;

                q.responses.forEach((resp) => {
                    html += `<label><input type="radio" name="q${index}" value="${escapeHtml(resp)}"> ${escapeHtml(resp)}</label>`;
                });

                html += `</div>`;
                container.innerHTML += html;
            });

            document.getElementById('submit-btn').style.display = 'block';
        }

        function gradeQuiz() {
            let score = 0;
            const blocks = document.querySelectorAll('.question-block');

            quizData.forEach((q, index) => {
                const block = blocks[index];
                const selected = document.querySelector(`input[name="q${index}"]:checked`);
                const labels = block.querySelectorAll('label');
                const correctText = String(q.correct).trim();
                const isRight = selected && selected.value.trim() === correctText;

                labels.forEach(label => {
                    const input = label.querySelector('input');
                    input.disabled = true;
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
                    verdict.textContent = '\u2713 Correct';
                } else {
                    block.classList.add('wrong');
                    verdict.classList.add('wrong');
                    verdict.textContent = selected
                        ? '\u2717 Incorrect \u2014 correct answer: ' + q.correct
                        : '\u2717 Not answered \u2014 correct answer: ' + q.correct;
                }
                block.insertBefore(verdict, block.children[1]);
            });

            const wrong = quizData.length - score;
            document.getElementById('results').innerHTML =
                `<div class="score">${score} / ${quizData.length}</div>` +
                `<div class="summary">${score} right, ${wrong} wrong</div>`;
            document.getElementById('submit-btn').style.display = 'none';
            document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
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
