test_components = {
'1_0_basic_assertion': """{
    "uid":"123abc",
    "recipient": {"identity": "test@example.com","hashed": false, "type": "email"},
    "badge": "http://a.com/badgeclass",
    "issuedOn": "2015-04-30",
    "verify": {"type": "hosted", "url": "http://a.com/instance"}
}""",
'1_0_basic_badgeclass': """{
    "name": "Basic Badge",
    "description": "Basic as it gets. v1.0",
    "image": "http://a.com/badgeclass_image",
    "criteria": "http://a.com/badgeclass_criteria",
    "issuer": "http://a.com/issuer"
}""",
'1_0_basic_issuer': """{
    "name": "Basic Issuer",
    "url": "http://a.com/issuer"
}""",
'1_0_assertion_with_errors': """{
    "uid":"123abc",
    "recipient": "test@example.com",
    "badge": "http://a.com/badgeclass",
    "issuedOn": "2015-04-30",
    "verify": {"type": "hosted", "url": "http://a.com/instance"}
}""",
'0_5_assertion': """{
    "recipient": "test@example.com",
    "badge": {
        "version": "0.5.0",
        "name": "Basic McBadge",
        "image": "http://oldstyle.com/images/1",
        "description": "A basic badge.",
        "criteria": "http://oldsyle.com/criteria/1",
        "issuer": {
            "origin": "http://oldstyle.com",
            "name": "Basic Issuer"
        }
    }
}""",
'0_5_1_assertion': """{
    "recipient": "sha256$85c4196c5516561cef673642157499b70066cb1070852b2a37fdbf3cc599b087",
    "salt": "sel gris",
    "issued_on": "2011-06-01",
    "badge": {
        "version": "0.5.0",
        "name": "Basic McBadge",
        "image": "http://oldstyle.com/images/2",
        "description": "A basic badge.",
        "criteria": "http://oldsyle.com/criteria/2",
        "issuer": {
            "origin": "http://oldstyle.com",
            "name": "Basic Issuer"
        }
    }
}""",
'1_0_basic_assertion_with_extra_properties': """{
    "uid":"123abc",
    "recipient": {"identity": "test@example.com","hashed": false, "type": "email"},
    "badge": "http://a.com/badgeclass",
    "issuedOn": "2015-04-30",
    "verify": {"type": "hosted", "url": "http://a.com/instance3"},
    "snood":"a very fun video game"
}""",
'2_0_basic_assertion': """{
  "@context": "https://w3id.org/openbadges/v2",
  "type": "Assertion",
  "id": "https://example.org/beths-robotics-badge.json",
  "recipient": {
    "type": "email",
    "hashed": true,
    "salt": "deadsea",
    "identity": "sha256$c7ef86405ba71b85acd8e2e95166c4b111448089f2e1599f42fe1bba46e865c5"
  },
  "image": "https://example.org/beths-robot-badge.png",
  "evidence": "https://example.org/beths-robot-work.html",
  "issuedOn": "2016-12-31T23:59:59Z",
  "badge": "https://example.org/robotics-badge.json",
  "verification": {
    "type": "hosted"
  }
}""",
'2_0_basic_badgeclass': """{
  "@context": "https://w3id.org/openbadges/v2",
  "type": "BadgeClass",
  "id": "https://example.org/robotics-badge.json",
  "name": "Awesome Robotics Badge",
  "description": "For doing awesome things with robots that people think is pretty great.",
  "image": "https://example.org/robotics-badge.png",
  "criteria": "https://example.org/robotics-badge.html",
  "issuer": "https://example.org/organization.json",
}""",
'2_0_basic_issuer': """{
  "@context": "https://w3id.org/openbadges/v2",
  "type": "Issuer",
  "id": "https://example.org/organization.json",
  "name": "An Example Badge Issuer",
  "url": "https://example.org",
  "email": "contact@example.org"
}""",
'openbadges_context': """
{"@context": {"issuedOn": {"@id": "obi:issueDate", "@type": "xsd:dateTime"}, "AlignmentObject": "schema:AlignmentObject", "uid": {"@id": "obi:uid"}, "claim": {"@id": "cred:claim", "@type": "@id"}, "targetCode": {"@id": "obi:targetCode"}, "image": {"@id": "schema:image", "@type": "@id"}, "Endorsement": "cred:Credential", "Assertion": "obi:Assertion", "related": {"@id": "dc:relation", "@type": "@id"}, "evidence": {"@id": "obi:evidence", "@type": "@id"}, "sec": "https://w3id.org/security#", "Criteria": "obi:Criteria", "owner": {"@id": "sec:owner", "@type": "@id"}, "revocationList": {"@id": "obi:revocationList", "@type": "@id"}, "targetName": {"@id": "schema:targetName"}, "id": "@id", "alignment": {"@id": "obi:alignment", "@type": "@id"}, "allowedOrigins": {"@id": "obi:allowedOrigins"}, "Profile": "obi:Profile", "startsWith": {"@id": "http://purl.org/dqm-vocabulary/v1/dqm#startsWith"}, "author": {"@id": "schema:author", "@type": "@id"}, "FrameValidation": "obi:FrameValidation", "validationFrame": "obi:validationFrame", "creator": {"@id": "dc:creator", "@type": "@id"}, "validationSchema": "obi:validationSchema", "validatesType": "obi:validatesType", "version": {"@id": "schema:version"}, "BadgeClass": "obi:BadgeClass", "endorsement": {"@id": "cred:credential", "@type": "@id"}, "revocationReason": {"@id": "obi:revocationReason"}, "RevocationList": "obi:RevocationList", "issuer": {"@id": "obi:issuer", "@type": "@id"}, "type": "@type", "email": {"@id": "schema:email"}, "targetDescription": {"@id": "schema:targetDescription"}, "schema": "http://schema.org/", "targetUrl": {"@id": "schema:targetUrl"}, "criteria": {"@id": "obi:criteria", "@type": "@id"}, "verificationProperty": {"@id": "obi:verificationProperty"}, "description": {"@id": "schema:description"}, "Extension": "obi:Extension", "tags": {"@id": "schema:keywords"}, "CryptographicKey": "sec:Key", "expires": {"@id": "sec:expiration", "@type": "xsd:dateTime"}, "hosted": "obi:HostedBadge", "dc": "http://purl.org/dc/terms/", "telephone": {"@id": "schema:telephone"}, "publicKey": {"@id": "sec:publicKey", "@type": "@id"}, "badge": {"@id": "obi:badge", "@type": "@id"}, "endorsementComment": {"@id": "obi:endorsementComment"}, "genre": {"@id": "schema:genre"}, "hashed": {"@id": "obi:hashed", "@type": "xsd:boolean"}, "recipient": {"@id": "obi:recipient", "@type": "@id"}, "HostedBadge": "obi:HostedBadge", "identity": {"@id": "obi:identityHash"}, "revoked": {"@id": "obi:revoked", "@type": "xsd:boolean"}, "verify": "verification", "VerificationObject": "obi:VerificationObject", "name": {"@id": "schema:name"}, "publicKeyPem": {"@id": "sec:publicKeyPem"}, "obi": "https://w3id.org/openbadges#", "url": {"@id": "schema:url", "@type": "@id"}, "cred": "https://w3id.org/credentials#", "Image": "obi:Image", "created": {"@id": "dc:created", "@type": "xsd:dateTime"}, "IdentityObject": "obi:IdentityObject", "signed": "obi:SignedBadge", "Evidence": "obi:Evidence", "narrative": {"@id": "obi:narrative"}, "caption": {"@id": "schema:caption"}, "audience": {"@id": "obi:audience"}, "extensions": "https://w3id.org/openbadges/extensions#", "verification": {"@id": "obi:verify", "@type": "@id"}, "xsd": "http://www.w3.org/2001/XMLSchema#", "TypeValidation": "obi:TypeValidation", "revokedAssertions": {"@id": "obi:revoked"}, "SignedBadge": "obi:SignedBadge", "validation": "obi:validation", "salt": {"@id": "obi:salt"}, "targetFramework": {"@id": "schema:targetFramework"}, "Issuer": "obi:Issuer"}}"""
}
