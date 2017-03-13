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
}"""
}
