"""Tool schema definitions for risk and compliance /tools/list endpoint."""

TOOLS = [
    {
        "name": "assess_order_risk",
        "description": (
            "Run a risk assessment on an order. Calculates a risk score based"
            " on order value and customer flags, records the assessment, and"
            " returns the score, triggered flags, and a decision of"
            " 'approve', 'review', or 'block'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to assess (e.g. ORD-201)",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_risk_assessment",
        "description": (
            "Retrieve an existing risk assessment for an order."
            " Returns the assessment ID, risk score, triggered flags,"
            " and decision if one has already been recorded."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to look up (e.g. ORD-201)",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "override_risk_decision",
        "description": (
            "Override a risk decision from 'review' to 'approve'."
            " Only assessments with a current decision of 'review' can be"
            " overridden. 'block' decisions cannot be overridden."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assessment_id": {
                    "type": "string",
                    "description": (
                        "The assessment ID to override (e.g. RISK-abc12345)"
                    ),
                },
                "new_decision": {
                    "type": "string",
                    "description": "The new decision — must be 'approve'",
                },
            },
            "required": ["assessment_id", "new_decision"],
        },
    },
    {
        "name": "flag_customer",
        "description": (
            "Flag a customer for future risk assessments."
            " Flagged customers will receive a higher risk"
            " score on all future orders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer ID to flag (e.g. C-301)",
                },
                "reason": {
                    "type": "string",
                    "description": (
                        "Reason for flagging (e.g. 'suspicious"
                        " activity', 'chargeback history')"
                    ),
                },
            },
            "required": ["customer_id", "reason"],
        },
    },
    {
        "name": "get_compliance_requirements",
        "description": (
            "Check what compliance requirements apply to an"
            " order. Returns a list of required checks such as"
            " high-value review or flagged customer review."
            " Returns an empty list for simple orders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to check (e.g. ORD-201)",
                },
            },
            "required": ["order_id"],
        },
    },
]
