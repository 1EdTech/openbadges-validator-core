from flask import Flask, redirect, render_template, request
import json
import six

from badgecheck.verifier import verify


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4mb file upload limit


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/results", methods=['POST'])
def results():
    if isinstance(request.form['data'], six.string_types) or request.files:
        user_input = request.form['data']
        if 'image' in request.files and len(request.files['image'].filename):
            user_input = request.files['image']
        verification_results = verify(user_input)
        return render_template(
            'results.html', results=json.dumps(verification_results, indent=4))

    return redirect('/')


if __name__ == "__main__":
    app.run()
