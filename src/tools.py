"""The order system the order agent talks to. A local mock, so the experiment
controls outages exactly. Tool calls still show up as execute_tool spans."""
import json
import uuid

from .config import DATA, TOOL_ERROR

ORDERS = json.loads((DATA / "orders.json").read_text(encoding="utf-8"))

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "get_order_status",
        "description": "Look up the current status of one order by its order ID.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "The 5-digit order ID."}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "create_return",
        "description": "Start a return for an order and get a return reference.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The 5-digit order ID."},
                "reason": {"type": "string", "description": "Why the customer is returning the item."},
            },
            "required": ["order_id", "reason"],
            "additionalProperties": False,
        },
    },
]


def run_tool(name: str, args: dict, condition: str, system_down: bool) -> str:
    if system_down:
        return TOOL_ERROR[condition]
    order_id = str(args.get("order_id", "")).strip().lstrip("#")
    order = ORDERS.get(order_id)
    if name == "get_order_status":
        if not order:
            return json.dumps({"error": f"No order found with ID {order_id}."})
        return json.dumps({"order_id": order_id, **order})
    if name == "create_return":
        if not order:
            return json.dumps({"error": f"No order found with ID {order_id}."})
        return json.dumps({"order_id": order_id, "return_id": f"R-{order_id}-{uuid.uuid4().hex[:4].upper()}",
                           "status": "return_created", "next_step": "A return label has been emailed to the customer."})
    return json.dumps({"error": f"Unknown tool {name}"})
