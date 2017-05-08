from flask import Flask, redirect, render_template, request
import json

from badgecheck.verifier import verify

from utils import validate_input

app = Flask(__name__)




@app.route("/")
def home():
    return render_template('index.html')


@app.route("/results", methods=['POST'])
def results():
    if validate_input(request.form['data']):
        user_input = request.form['data']
        verification_results = verify(user_input)
        return render_template(
            'results.html', results=json.dumps(verification_results, indent=4))

    return redirect('/')


if __name__ == "__main__":
    app.run()
