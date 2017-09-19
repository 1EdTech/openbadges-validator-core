"""
These files are present to generate test mocks only. They will be moved out of the package into the testfiles directory
in a future 1.x release.
"""


class ExampleExtension(object):
    name = 'Example Extension'
    context_url = 'https://w3id.org/openbadges/extensions/exampleExtension/context.json'
    rdf_type = 'extensions:ExampleExtension'

    context_json = {
      "@context": {
        "obi": "https://w3id.org/openbadges#",
        "extensions": 'https://w3id.org/openbadges/extensions#',
        "exampleProperty": "http://schema.org/text"
      },
      "obi:validation": [
        {
          "obi:validatesType": "extensions:ExampleExtension",
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
    context_url = 'http://w3id.org/openbadges/extensions/applyLinkExtension/context.json'
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
                "obi:validationSchema": "https://w3id.org/openbadges/extensions/applyLinkExtension/schema.json"
            }
        ]
    }

    validation_schema = {
        'https://w3id.org/openbadges/extensions/applyLinkExtension/schema.json': {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "title": "Apply Link",
            "description": "An extension that allows you to add a single url to a web page providing information on how earners may apply for a badge.",
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri"
                }
            },
            "required": ["url"]
        }
    }


class GeoLocation(object):
    name = 'Geo Location'
    context_url = 'https://w3id.org/openbadges/extensions/geoCoordinatesExtension/context.json'
    rdf_type = 'extensions:GeoCoordinates'

    context_json = {
        "@context": {
            "obi": "https://w3id.org/openbadges#",
            "schema": "http://schema.org/",
            "extensions": "https://w3id.org/openbadges/extensions#",
            "geo": "schema:geo",
            "name": "schema:name",
            "description": "schema:description",
            "latitude": "schema:latitude",
            "longitude": "schema:longitude"
        },
        "obi:validation": [
            {
                "obi:validatesType": "extensions:GeoCoordinates",
                "obi:validationSchema": "https://w3id.org/openbadges/extensions/geoCoordinatesExtension/schema.json"
            }
        ]
    }

    validation_schema = {
        'https://w3id.org/openbadges/extensions/geoCoordinatesExtension/schema.json': {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "title": "GeoCoordinates Open Badges Extension",
            "description": "An extension allowing for the addition of the geographic coordinates associated with a badge object. For example, geolocation could represent where a Badge Class is available, where a badge was earned or the location of an issuer. The required description property allows implementers to be more specific about the reason location is included. Implements Schema.org's Place class",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "geo": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"}
                    },
                    "required": ["latitude", "longitude"]
                }
            },
            "required": ["description", "geo"]
        }
    }


ALL_KNOWN_EXTENSIONS = {
    'extensions:ApplyLink': ApplyLink,
    'extensions:ExampleExtension': ExampleExtension,
    'extensions:GeoCoordinates': GeoLocation
}
