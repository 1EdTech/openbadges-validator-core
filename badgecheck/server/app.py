from flask import Flask, redirect, render_template, request
import json
import six

from badgecheck.verifier import verify


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4mb file upload limit


def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/results", methods=['GET'])
def result_get_redirect():
    return redirect('/')


@app.route("/results", methods=['POST'])
def results():
    data = request.get_json()
    profile = None
    if not data and isinstance(request.form['data'], six.string_types) or request.files:
        user_input = request.form['data']
        if 'image' in request.files and len(request.files['image'].filename):
            user_input = request.files['image']

        try:
            profile = json.loads(request.form['profile'])
        except (TypeError, ValueError):
            profile = None
    elif data:
        user_input = data.get('data')
        try:
            profile = data['profile']
            if isinstance(profile, six.string_types):
                profile = json.loads(profile)
        except (TypeError, ValueError, KeyError):
            pass

    verification_results = verify(user_input, recipient_profile=profile)

    if request_wants_json():
        return json.dumps(verification_results, indent=4), 200, {'Content-Type': 'application/json'}
    return render_template(
        'results.html', is_valid=verification_results.get('report', {}).get('valid'),
        error_count=verification_results.get('report', {}).get('errorCount'),
        results=json.dumps(verification_results, indent=4))


if __name__ == "__main__":
    app.run()
