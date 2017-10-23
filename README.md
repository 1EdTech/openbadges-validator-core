# Open Badges Validator Core

Open Badges Validator Core is a python package designed to verify the validity of Open Badges based on a variety of input sources and present a useful interface for accessing their properties and validation information. HTTP, Python and command line APIs are provided.

Open Badges Validator Core is released by [IMS Global Learning Consortium](https://www.imsglobal.org).

This package builds on Badgecheck, originated by [Concentric Sky](https://concentricsky.com). Other IMS Global members who have contributed to this package include [D2L](https://www.d2l.com/) and [Chalk & Wire](http://www.chalkandwire.com).

## User documentation

### Installing the package

For best results, [create and activate a local virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

You may install the validator directly from [pypi](https://pypi.python.org/pypi/openbadges/): `pip install openbadges`

### Running the validator over the command-line

When installed into an activated environment, a command line script will be available.

`openbadges verify --data 'https://example.org/badgeassertion'`

See help with `openbadges verify --help`

There are two optional positional arguments, *input_file* and *output_file*. If you don't specify an output file, results will be written to stdout.
If you wish to provide input data, such as a URL from the command and write JSON results to an output file, you may use a `-` to skip the first input_file argument.
`openbadges verify - results.json --data 'https://example.org/badgeassertion'`

You may pass a JSON string of an expected recipient profile:
`openbadges verify input.json --recipient '{"email": "me@example.org", "url": "http://example.org"}'

### Running the Flask server

A Flask web server is an optional component of the Open Badges validator. The necessary dependency is installed when you install from `pip install -r requirements.txt`. You may install the server using pip with the optional server flag: `pip install openbadges [server]`

In order to run the server, activate your environment, navigate to the folder that was installed, and execute the following command: `python openbadges/verifier/server/app.py`

A local server will start up on the development port 5000 (by default), which you can access from your browser or other HTTP client.

### Interpreting the results

The results returned by the validator is a JSON object. (If you are using a user interface of some kind, you may not see this.) Depending on your use case, you may only be interested in a few parts of this object. The overall structure of the returned object is

```
{
 "report": {...}
 "input": {...}
 "graph" {...}
}
```

… where the `report` object is the one you would typically be most interested in. If the `valid` property of the report object is set to `true`, it tells you that the validator did not find any errors when analyzing your badge.  If it is set to `false`, it means that your badge did contain at least one error. Check the `errorCount` property to find out how many errors there were. For each one of those errors, there will be a corresponding message (with a `messageLevel` of 'ERROR') in the `messages` array.

The validator may also issue warnings (these have a `messageLevel` of 'WARNING') in the `messages` array). A warning signals the presence of a feature in your badge which is discouraged, deprecated, risky, or generally considered not recommended practice. Your badge however remains valid and can safely be publicized. Correcting a warning is in other words optional.

The `input` object of the results object shows what input you provided to the validator. You will probably already know what you just submitted; this field is primarily meant for machines to confirm after the fact exactly which input data resulted in the given report.

The `graph` object contains a compact representation of the badge data, including parts of the badge that were fetched over the wire. This can be helpful for debugging, if you’re an expert.  

Note that a detailed technical description of the result objects and properties are provided in the HTTP API results section in this document.

### What versions of Open Badges does this validator support?

This is primarily a validator for Open Badges 2.0 and later. You can submit badges that were created under earlier versions of the Open Badges specification as well; note however that Open Badges 2.0 rules will be applied to such badges, and as a consequence of this, the validator may flag a badge as invalid that was flagged as valid by earlier validators.

If the version of your submitted badge is lower than 2.0, the validator will  (as represented in the report’s graph object) attempt to upgrade the badge to 2.0 syntax. The graph object can consequently be used as a part in the tool chain for forward migration of badges to the current version of the Open Badges standard.

### How do I fix errors with badges?

The Open Badges Validator is (unfortunately) not a repair tool, though if you are the issuer, you may find the error messages the validator reports essential in identifying the errors. Errors are typically fixed by modifying one or more of the objects that make up the badge. Error messages typically target a node_id or node_path in the message that identifies the location of the error, and the message aims to be as descriptive as possible of what was found to be invalid. Note that beyond the error messages themselves, the `graph` object of the report may provide helpful clues to pinpoint the error.

### Support

If you run into problems after following the installation and running instructions above, or if you have other kinds of questions relating to the use of the tool and/or the interpretation of results, please use the [IMS Open Badges Community forum](https://www.imsglobal.org/forums/open-badges-community-forum/open-badges-community-discussion) to ask your questions (and/or help others).

## How to contribute

If you have found what might be a bug in the application, open an issue in the [issue tracker](https://github.com/IMSGlobal/openbadges-validator-core/issues) with the label ‘bug’. The project owners will discuss the issue with you, and if it is indeed a bug, the issue will be confirmed and dealt with. (For general usage questions, please use the [IMS Open Badges Community forum](https://www.imsglobal.org/forums/open-badges-community-forum/open-badges-community-discussion) instead of the issue tracker. See the Support section in this document).

If you are a developer and want to contribute to the project, please begin with opening an issue in the tracker describing the change or addition you want to contribute. If we after discussing the matter can confirm the usefulness of your planned contribution, then get ready to contribute. We follow the [standard git flow for contributing to projects](https://git-scm.com/book/en/v2/GitHub-Contributing-to-a-Project), in other words, using pull requests from topic branches, followed by review by a project owner before merge.

Note that the open source license of this project will apply to your inbound contributions. Note also that under certain circumstances an IMS contributor agreement will need to be filled in. (This is one of the main reasons we want you to talk to us in the issue tracker before you spend time on coding).

## Developer documentation

### Design overview

This Open Badges verification and validation tool is based on principles of easy testing of modular components and consistent patterns of interaction between those components. It relies on the Redux pattern from the ReactJS community. We use the Python port of some of the basic Redux tools called Pydux.

Applications that implement Redux have several important characteristics that together make for predictable operation and division of responsibilities:

- Single source of truth: There is one object tree that represents the entire state of the application. It is managed in a “store” and expressed in simple data types.
- This state is read-only and can only be modified by submitting “actions”, that are handled by the store one at a time, always producing a new copy of the state. Because python variables are pointers to memory space, this makes for efficient storage and comparison. Actions are simple dicts with a “type” property.
- The mechanism for changing state occurs through “reducers”, which inspect incoming actions and return a new copy of the portion of the state they oversee.

In order to verify the integrity of Open Badges, the validator must take input from the user, analyze that input, access the relevant Open Badges resources, ensure that each of them are well formed and that they are linked together appropriately before packaging up the results and returning them to the user. This entails the ability to handle a wide variety of different inputs and configurations of badge resources. The validator takes advantage of Redux patterns to keep track of not only the badge data but also the processing tasks. All application state for a request is in a state object dict managed by a store created upon user input.

Open Badges Validator Core is made up of several important components:

- Action creators: These take input parameters and return an action dict that may be interpreted by the reducers. Each action creator returns a dict with a certain ‘type’ value that will be handled by one or more parts of the reducer tree.
- Reducers: These all have the function signature reducer(state, action) and return a new copy of the state object or the current object if no change has been made. Reducers are “combined” to each only need to manage one part of the overall state tree. Reducers cannot dispatch new actions, make API calls or do anything else that introduces side effects beyond returning their portion of the application state.
- Tasks: Within the state tree is a list of tasks, stored with their results. Tasks may do the things that the reducers are not allowed to do, like make HTTP requests and queue additional tasks (by calling the add_task action creator and returning the task to the task manager). Every task has the function signature task(state, task_meta) and returns a tuple in the format (result: bool, message: str, actions: list[dict]), made easier with the helper task_result()
- Validation Tasks (specifically): Tasks are broken down to a micro level with a single responsibility each. Because of their functional structure that inspects state and returns results at this level, they are very testable.
- User API and task manager: The application state is created fresh with each request. When a request comes in, the request manager initializes a store and queues up the first relevant tasks. Then, while tasks remain, the task manager runs each of them and dispatches the actions that they return, some of which queue up new tasks.
- Tests: Unit tests and integration tests cover action creators, reducers, tasks, and API response. Mock state objects and actions are particularly easy to construct, and tests may implement their own task running system in order to precisely limit what components of the system are under test at any given time. Everything boils down to specifying which changes to state should occur and verifying that they do occur.

When the tasks run out, the user API returns the state to the user.

### HTTP API
The Open Badges Validator includes a simple Flask server application for your convenience (refer to “Running the Flask server” in this document). When the server is running, it responds primarily to POST requests at `/results`.

#### Request Parameters

Make a request to `/results` with either a JSON body or form/multipart. If using image, use `form/multipart`. Responses may be requested in either `text/html` or `application/json` format.

| name | Expected value(s) | Required? |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| data | One of: a) URL string for an HTTP-hosted Open Badges Object, b) JSON string for an Open Badges Object, or c) Cryptographic signature string (JWS format) of a signed Open Badges Assertion | One of `data` or `image` is required. |
| image | File: A baked Open Badge image in PNG or SVG format. See [Baking Specification](https://openbadgespec.org/baking/index.html). | One of `data` or `image` is required. |
| profile | JSON string of an Open Badges Profile that is trusted by the client. If an Assertion is found in the “data” or “image” input, the profile will be checked against its recipient value. If input data is not an Assertion, profile will be ignored.  | No. |

#### Example Request

Here is the essential parts of an example request sent in form/multipart format.

```
Request URL: http://localhost:8000/results
Request Method: POST
Accept: application/json

------WebKitFormBoundaryaBQaPAkvF3DXppQ7
Content-Disposition: form-data; name="data"

https://api.badgr.io/public/assertions/Ph_r3S6jTqqkHNrQUKbqQg?v=2_0
------WebKitFormBoundaryaBQaPAkvF3DXppQ7
Content-Disposition: form-data; name="image"; filename=""
Content-Type: application/octet-stream

------WebKitFormBoundaryaBQaPAkvF3DXppQ7
Content-Disposition: form-data; name="profile"

{"email": "nate@ottonomy.net"}
------WebKitFormBoundaryaBQaPAkvF3DXppQ7--
```

A HTML form is available in browser by making a GET request to the root of the server. If the flask server is running on http://127.0.0.1:8000 for example, a request may be made to that URL to obtain the form in the browser.

#### Response

The response will be delivered as a JSON object, either as the complete body of a request for “application/json” or embedded in an HTML results template.

| Response property | type/description |
| -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| input | An object summarizing the request that was made. (Input object) |
| graph  |Array of objects: The unordered set of linked data objects discovered during validation of the input. Each will be compacted into the Open Badges V2 Context and  tagged with at ‘type’ and an ‘id’. |
| report | An object summarizing the validity results and the object in the graph that is the primary subject of validation (see Report object below) |

Here are the properties found within the 'report':

| Report Object property | type/description |
| -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| recipientProfile | An object describing the matching recipient identifier property of the submitted recipientProfile. For example, if a Profile with three possible email addresses was submitted and the Assertion was awarded to one of them, the recipientProfile would be an object with a single “email” property that had a single string value of the successfully confirmed address. If a “url”-type identifier was the recipient identifier property in a validated assertion, the property name in recipientProfile would be “url”. |
| valid | Boolean: Whether the object parsed from the input passed all required verification and data validation tests. |
| errorCount | Number (int): The number of critical verification and validation task failures (violations of MUST-level requirements in the Open Badges Specification). If this number is > 0, valid will be false. |
| warningCount | Number (int): The number of non-critical verification and validation task failures (violations of SHOULD-level requirements). These will not cause the badge to be invalid, but consumers MAY treat Open Badge objects that fail these tasks as invalid for certain purposes. |
| messages | Array of Message objects (see below) |
| validationSubject | String: the id matching the ‘id’ property of the object in the response ‘graph’ that is the primary thing validated. For example, if the URL of a hosted Assertion is the input data, this will be that URL. |
| openBadgesVersion | A string corresponding to the detected version of the validationSubject. Possible values are “0.5”, “1.0”, “1.1” and “2.0” |

Here are the properties that describe each of the 'messages' in the report:

| Message Object property | type/description |
| -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| name | A string codename for the task being reported. May not appear for “INFO” level messages. |
| messageLevel | A string describing the severity of the message. Either “ERROR” (critical, triggering invalidity of the overall result), “WARNING” (non-critical), or “INFO” (interesting tidbit). |
| node_id | String: the “id” matching the subject in the graph that was tested for this particular task. |
| node_path | Node Path Array (see note below)
| success | Boolean: Whether the task succeeded or failed. Successful task results are omitted from the response (except “INFO” messages). |
| result | String: A human-readable description of the problem or informative message. |
| *other properties* | Other properties vary by task. They provide debug information to describe the information made available to the task and should typically be ignored by the client. |

**Node Path Array**: A specialized Array used by the validator to locate a node that is nested within one of the primary objects in the graph. For example `[“http://foo.co/bar”, “alignment”, 0, “alignmentName”]` indicates the “alignmentName” property of the object that is the first (index 0) entry in the list of “alignment” objects of the node with the id “http://foo.co/bar” in the graph.

### Python API

In addition to the HTTP server included with the package, a python API is available. Response properties are the same, delivered as a python dictionary instead of a JSON string.

To make a request using the python API from within a python application, make sure the package is installed into your python environment (likely an activated virtualenv). Then import the verify method and call it:

```
from openbadges import verify
results = verify(‘http://assertions.com/example-assertion-url’)
```

If you wish to verify assertion input against an expected recipient profile, you may pass the profile dict as a second positional argument:

`results = verify(assertion_json, {‘email’: [‘possible@example.com’, ‘other@example.com’]}`

### Using your own cache backend

This package makes use of RequestsCache to reduce load on frequently used resources such as the core Open Badges context files. By default, the validator will instantiate its own in-memory cache, but it is possible to pass in a compatible RequestsCache backend of your own with higher performance in the optional “options” keyword arguments dict. This way, you can reuse the cache across multiple validation requests.

`results = verify(assertion_url, options={‘cache_backend’: ‘redis’, ‘cache_expire_after’: 60 * 60 * 24})`

### Running tests
To run tests, install tox into your system's global python environment and use the command: `tox`
