# AI Quiz Generator

A small web app that uses Google's Gemini AI to write a multiple-choice quiz on any topic you choose. Pick a topic, a number of questions, and a difficulty, then take the quiz right in your browser and see exactly which answers you got right and wrong.

## Features

- **Any topic:** type in whatever you like, such as History, Space, Biology, or Movies.
- **Adjustable quiz:** choose 1 to 20 questions and easy, intermediate, or hard difficulty.
- **Instant grading:** submit your answers to see your score, with correct answers shown in green and wrong ones in red.
- **Clean interface:** progress bar, lettered answer choices, and a score summary at the end.
- **Runs locally:** a simple Flask server you start on your own computer.

## How it works

1. The browser asks the Flask server for a quiz.
2. The server sends a prompt to the Gemini API asking for a JSON list of questions, answer choices, and the correct answer.
3. The page displays the questions and grades your answers in the browser.

## Requirements

- Python 3.9 or newer
- A Google Gemini API key
- The packages `flask`, `google-genai`, and `python-dotenv`

## Setup

1. Install the dependencies:

   ```
   pip install flask google-genai python-dotenv
   ```

2. Create a file named `.env` in the same folder as `main.py` containing one line:

   ```
   KEY=your_gemini_api_key
   ```

   Don't use quotes or spaces around the `=`. Never share this file or upload it to GitHub.

3. Start the app:

   ```
   python main.py
   ```

4. Open http://localhost:8080 in your browser.

## Customizing the quiz

Use the form at the top of the page, or set the options in the address bar:

```
http://localhost:8080/?topic=Space&num_q=3&diff=hard
```

| Option   | Meaning                          | Default        |
|----------|----------------------------------|----------------|
| `topic`  | What the quiz is about           | History        |
| `num_q`  | Number of questions              | 5              |
| `diff`   | `easy`, `intermediate`, or `hard`| intermediate   |
| `lang`   | Language of the quiz             | English        |

To use a different port, set the `PORT` environment variable before starting the app.

## Troubleshooting

- **"Could not find an API key":** check that the file is named exactly `.env` (not `.env.txt`) and sits next to `main.py`. The message shows where the app looked.
- **"Could not load quiz" on the page:** the AI request failed. The reason is shown on the page and in the terminal. Check your API key and the `MODEL` name near the top of `main.py`.
- **Blank or odd quiz:** click "Generate New Quiz" to try again, since the AI occasionally returns a badly formatted response.

## Security note

The API key is read from the `.env` file and is not stored in the code. Add `.env` to a `.gitignore` file so it is never committed.

## Built with

- [Flask](https://flask.palletsprojects.com/) for the web server
- [Google Gemini API](https://ai.google.dev/) for generating the questions
- Plain HTML, CSS, and JavaScript for the interface


<img width="910" height="883" alt="image" src="https://github.com/user-attachments/assets/53617e17-8def-4e8d-9ea6-458d0d972d82" />

