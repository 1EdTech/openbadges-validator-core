badgecheck
==========

Badgecheck (codename for Open Badges Validator Core) is a python package
designed to verify the validity of Open Badges based on a variety of input
sources and present a useful interface for accessing their properties and
validation information. Python and command line APIs are provided.

**Note - Badgecheck is in *early beta* stage. The results provided *cannot*
be used as a reliable indicator of the validity of an Open Badge, and *cannot*
be used as proof to claim implementation conformance.**

If you want to validate 1.0 or 1.1 badges in the meanwhile, please use
https://badgecheck.io.

Badgecheck was originated by Concentric Sky. https://concentricsky.com
This version of badgecheck is released by IMS Global Learning Consortium.

Installation
------------

You may install badgecheck directly from pypi:
`pip install badgecheck`

To contribute to development and run tests, there are a couple additional
requirements to install. Clone the git repository, activate a local virtualenv,
and use the command:
`pip install -r requirements.txt` from the project root directory.

To run tests, install tox into your system's global python environment and
use the command:
`tox`

Follow issues and contribute to the badgecheck roadmap:
https://github.com/openbadges/badgecheck/issues

How to run the web server
-------------------------

A Flask webserver is an optional component of badgecheck. The necessary
dependency is installed when you install from
`pip install -r requirements.txt`.
You may install the server using pip with the optional server flag:
`pip install badgecheck [server]`

In order to run the server, activate your environment and execute the following
command:
`python badgecheck/server/app.py`

A local server will start up on the development port 5000 (by default), which
you can access from your browser.

Design Overview for Developers
------------------------------

This Open Badges verification and validation tool is based on principles of
easy testing of modular components and consistent patterns of interaction
between those components. It relies on the `Redux <http://redux.js.org//>`_
pattern from the ReactJS community. We use the Python port of some of the basic
Redux tools called Pydux.

Applications that implement Redux have several important characteristics that
together make for predictable operation and division of responsibilities:

* Single source of truth: There is one object tree that represents the entire
  state of the application. It is managed in a "store" and expressed in simple
  data types.
* This state is read-only and can only be modified by submitting "actions",
  that are handled by the store one at a time, always producing a new copy
  of the state. Because python variables are pointers to memory space, this
  makes for efficient storage and comparison. Actions are simple dicts with
  a "type" property.
* The mechanism for changing state occurs through "reducers", which inspect
  incoming actions and return a new copy of the portion of the state they
  oversee.

In order to verify the integrity of Open Badges, badgecheck must take input
from the user, analyze that input, access the relevant Open Badges resources,
ensure that each of them are well formed and that they are linked together
appropriately before packaging up the results and returning them to the user.
This entails the ability to handle a wide variety of different inputs and
configurations of badge resources. Badgecheck takes advantage of Redux patterns
to keep track of not only the badge data but also the processing tasks. All
application state for a request is in a state object dict managed by a store
created upon user input.

Badgecheck is made up of several important components:

* Action creators: These take input parameters and return an action dict that
  may be interpreted by the reducers. Each action creator returns a dict with
  a certain 'type' value that will be handled by one or more parts of the
  reducer tree.
* Reducers: These all have the function signature ``reducer(state, action)``
  and return a new copy of the state object or the current object if no change
  has been made. Reducers are "combined" to each only need to manage one part
  of the overall state tree. Reducers cannot dispatch new actions, make API
  calls or do anything else that introduces side effects beyond returning their
  portion of the application state.
* Tasks: Within the state tree is a list of tasks, stored with their results.
  Tasks may do the things that the reducers are not allowed to do, like make
  HTTP requests and queue additional tasks (by calling the ``add_task`` action
  creator and returning the task to the task manager). Every task has the
  function signature ``task(state, task_meta)`` and returns a tuple in the
  format ``(result: bool, message: str, actions: list[dict])``, made easier
  with the helper ``task_result()``
* Validation Tasks (specifically): Tasks are broken down to a micro level with
  a single responsibility each. Because of their functional structure that
  inspects state and returns results at this level, they are very testable.
* User API and task manager: The application state is created fresh with each
  request. When a request comes in, the request manager initializes a store
  and queues up the first relevant tasks. Then, while tasks remain, the task
  manager runs each of them and dispatches the actions that they return, some
  of which queue up new tasks.
* Tests: Unit tests and integration tests cover action creators, reducers,
  tasks, and API response. Mock state objects and actions are particularly
  easy to construct, and tests may implement their own task running system
  in order to precisely limit what components of the system are under test
  at any given time. Everything boils down to specifying which changes to
  state should occur and verifying that they do occur.

When the tasks run out, the user API returns the state to the user. The final
1.0 API contract has not been finalized.
