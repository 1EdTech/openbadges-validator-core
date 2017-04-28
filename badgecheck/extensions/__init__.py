"""
Developer Warning:
The badgecheck.extensions package contains information about published extension contributed
by the Open Badges community. This package will be refactored to support all general extensions, 
after which specific information about each extension may be pulled back out. Do not import
from this package.
"""


class ExampleExtension(object):
    name = 'Example Extension'
    context_url = 'https://w3id.org/openbadges/extensions/exampleExtension/context.json'
    rdf_type = 'extensions:ExampleExtension'

    context_json = {
      "@context": {
        "obi": "https://w3id.org/openbadges#",
        "exampleProperty": "http://schema.org/text"
      },
      "obi:validation": [
        {
          "obi:validatesType": "obi:extensions/#ExampleExtension",
          "obi:validationSchema": "https://w3id.org/openbadges/extensions/exampleExtension/schema.json"
        }
      ]
    }

    validation_schema = {
        "https://w3id.org/openbadges/extensions/exampleExtension/schema.json": {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "title": "1.1 Open Badge Example Extension",
            "description": "An extension that allows you to add a single string exampleProperty to an extension object to represent some of your favorite text.",
            "type": "object",
            "properties": {
                "exampleProperty": {
                    "type": "string"
                }
            },
            "required": ["exampleProperty"]
        }
    }


class ApplyLink(object):
    name = 'Apply Link'
    context_url = 'http://openbadgespec.org/extensions/applyLinkExtension/context.json'
    rdf_type = 'extensions:ApplyLink'

    context_json = {
        "@context": {
            "obi": "https://w3id.org/openbadges#",
            "extensions": "https://w3id.org/openbadges/extensions#",
            "url": "extensions:applyLink"
        },
        "obi:validation": [
            {
                "obi:validatesType": "extensions:ApplyLink",
                "obi:validationSchema": "https://openbadgespec.org/extensions/applyLinkExtension/schema.json"
            }
        ]
    }

    validation_schema = {
        'key': {}
    }


ALL_KNOWN_EXTENSIONS = {
    'extensions:ApplyLink': ApplyLink,
    'extensions:ExampleExtension': ExampleExtension
}
