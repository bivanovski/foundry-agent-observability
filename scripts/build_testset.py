"""Builds data/testset.jsonl: 40 questions with ground truth.

Edit the questions here, never in the .jsonl, and re-run:
    python scripts/build_testset.py

Design (frozen before the main run, see results/CHANGELOG.md, 2026-11-16 "test set v2"):
  P  12 policy questions (mistake 1): 8 prior_conflict (a generic answer is wrong for VoltCart), 4 easy
  O  12 order questions (mistake 2): 4 id_first, 4 id_buried (ID among other numbers, incl. 5-digit decoys), 4 no_id
  X   8 questions while the order system is down (mistake 3): 6 plain, 2 insist ("please try again")
  R   8 controls: 5 off_topic/social (route none), 3 uncovered (policy questions the documents do not cover)

Fields
  id                 stable question id
  scenario           mistake1 | mistake2 | mistake3 | control
  category           policy | order_id | order_return | order_noid | outage | routine
  subtype            prior_conflict | easy | id_first | id_buried | no_id | plain | insist | social | uncovered
  message            what the customer writes
  expected_route     policy | order | none
  order_system       up | down   (down = the order system is simulated as unavailable)
  expected_order_id  the only order id a tool may be called with (order questions)
  expected_tool      tool that must be called (or null)
  expected_facts     facts a correct answer must contain (the judge checks these)
  expected_behavior  what a correct answer does, in one sentence
"""
import json
from pathlib import Path

Q = []


def add(id, scenario, category, subtype, message, route, behavior, facts=(), order_id=None,
        tool=None, system="up"):
    Q.append(dict(id=id, scenario=scenario, category=category, subtype=subtype, message=message,
                  expected_route=route, order_system=system, expected_order_id=order_id,
                  expected_tool=tool, expected_facts=list(facts), expected_behavior=behavior))


# ---------- Mistake 1: the agent that didn't look it up (12 policy questions) ----------
P = ("mistake1", "policy")
# easy: a generic store answer happens to be right
add("P01", *P, "easy", "I bought a pair of over-ear headphones 40 days ago and I'd like to return them. Is that still possible?",
    "policy", "Says the return is not possible because the 30-day window from delivery has passed.",
    ["Return window is 30 days from delivery", "A return after 40 days is not accepted"])
add("P02", *P, "easy", "I opened a pair of wireless earbuds 5 days ago and I don't like the sound. Can I return them?",
    "policy", "Says opened in-ear headphones/earbuds cannot be returned once the hygiene seal is broken unless defective.",
    ["Earbuds cannot be returned once the hygiene seal is broken", "Exception only if defective"])
add("P03", *P, "easy", "I dropped my phone and the screen cracked. Will the warranty cover the repair?",
    "policy", "Says accidental damage such as cracked screens is not covered by the standard warranty.",
    ["Accidental damage is not covered by the standard warranty"])
add("P04", *P, "easy", "I got a VoltCart gift card that I won't use. Can I return it for a refund?",
    "policy", "Says gift cards cannot be returned or refunded.", ["Gift cards cannot be returned or refunded"])
# prior_conflict: the plausible generic answer is wrong for VoltCart
add("P05", *P, "prior_conflict", "I opened my new laptop 10 days ago and it's not for me. Can I send it back?",
    "policy", "Says yes, and mentions the 15% restocking fee for opened laptops.",
    ["The return is allowed (within 30 days)", "A 15% restocking fee applies to opened laptops"])
add("P06", *P, "prior_conflict", "Once you receive my returned item, how long until I get my money back?",
    "policy", "Says refunds are issued within 14 days of the item arriving at the warehouse.",
    ["Refund within 14 days of the item arriving", "Refund goes to the original payment method"])
add("P07", *P, "prior_conflict", "I just changed my mind about a blender I bought. Who pays the shipping to send it back?",
    "policy", "Says the customer pays a flat 4.99 EUR return shipping fee deducted from the refund.",
    ["Customer pays return shipping when they changed their mind", "The fee is 4.99 EUR"])
add("P08", *P, "prior_conflict", "My phone was delivered on 1 December. Today is 10 January. Can I still return it?",
    "policy", "Says yes, because the holiday extension allows returns until 15 January for items delivered 15 Nov to 24 Dec.",
    ["Holiday extension applies to deliveries from 15 November to 24 December", "Return allowed until 15 January"])
add("P09", *P, "prior_conflict", "How long is the warranty on a TV I bought from you?",
    "policy", "Says 24 months from delivery.", ["Warranty is 24 months"])
add("P10", *P, "prior_conflict", "The battery in my laptop barely holds a charge after 14 months. Is that covered by warranty?",
    "policy", "Says no, batteries are covered for 12 months only.", ["Batteries are covered for 12 months only", "Not covered at 14 months"])
add("P11", *P, "prior_conflict", "Can I still buy CarePlus for a laptop that was delivered two months ago?",
    "policy", "Says no, CarePlus must be bought within 30 days of delivery.", ["CarePlus can only be bought within 30 days of delivery"])
add("P12", *P, "prior_conflict", "In general, does your 30-day return period start on the day I place the order or on the day it is delivered? "
    "Delivery sometimes takes over a week.",
    "policy", "Says the 30-day window starts on the delivery date, not the order date.",
    ["The 30-day window starts on the delivery date, not the order date"])

# ---------- Mistake 2: the handoff that dropped the order number (12 order questions) ----------
M = ("mistake2",)
# id_first: the ID is in the first sentence
add("O01", *M, "order_id", "id_first", "Where is my order 48213? It was supposed to arrive on Monday.",
    "order", "Reports that order 48213 is delayed at the sorting centre with a new estimate of 23 November.",
    ["Order 48213 is delayed", "New estimated delivery is 23 November"], order_id="48213", tool="get_order_status")
add("O02", *M, "order_id", "id_first", "I placed order 72560 for a gaming laptop on Sunday and it still says processing. When will it ship?",
    "order", "Reports that order 72560 is waiting to be packed and ships within 1 business day.",
    ["Order 72560 is still processing", "Ships within 1 business day"], order_id="72560", tool="get_order_status")
add("O03", *M, "order_id", "id_first", "Why was my tablet order #90031 cancelled??",
    "order", "Explains order 90031 was cancelled because the bank declined the payment.",
    ["Order 90031 was cancelled", "The payment was declined by the bank"], order_id="90031", tool="get_order_status")
add("O04", *M, "order_return", "id_first", "Please start a return for order 27745. The wireless mouse double-clicks on its own.",
    "order", "Starts a return for order 27745 and gives the return reference.",
    ["A return was created for order 27745", "Gives a return reference number"], order_id="27745", tool="create_return")
# id_buried: the ID comes late, among other numbers (5-digit decoys included)
add("O05", *M, "order_id", "id_buried", "Hi, this is Ana Trajkovska from Skopje, postcode 10000. I paid 89.99 EUR on 12 November and was told "
    "it would come by the 18th. You can call me on 070 123 456. I need it for a job interview on Friday. My order number is 51877. Any news?",
    "order", "Reports that order 51877 is out for delivery today. Does not use the postcode, phone number or amount as an order id.",
    ["Order 51877 is out for delivery today"], order_id="51877", tool="get_order_status")
add("O06", *M, "order_id", "id_buried", "My postcode is 11000 and my phone is 064 222 3344. I spent 249 EUR on a smartwatch on 14 November, "
    "order 15428. When does it arrive?",
    "order", "Reports that order 15428 was handed to DHL with estimated delivery on 21 November. Does not use the postcode as an order id.",
    ["Order 15428 is shipped with DHL", "Estimated delivery is 21 November"], order_id="15428", tool="get_order_status")
add("O07", *M, "order_return", "id_buried", "I got the mechanical keyboard on 7 November, paid 119 EUR, invoice 20264, customer number 77310. "
    "Order number 60412. The keys feel wrong and I want to return it.",
    "order", "Starts a return for order 60412 and gives the return reference. Does not use the invoice or customer number as an order id.",
    ["A return was created for order 60412", "Gives a return reference number"], order_id="60412", tool="create_return")
add("O08", *M, "order_id", "id_buried", "Graphics card, ordered two weeks ago, 649 EUR, paid with the card ending 4417, delivery to postcode 21000. "
    "It's order 39916. Nothing has happened, what's going on?",
    "order", "Explains the item in order 39916 is back-ordered and expected to ship on 2 December. Does not use the postcode as an order id.",
    ["The graphics card is back-ordered", "Expected to ship on 2 December"], order_id="39916", tool="get_order_status")
# no_id: no order number at all, the agent must ask
add("O09", *M, "order_noid", "no_id", "Where is my order? It's three days late and nobody tells me anything.",
    "order", "Asks the customer for their order number. Does not look up or invent an order.", ["Asks for the order number"])
add("O10", *M, "order_noid", "no_id", "I want to return the speaker I bought last week.",
    "order", "Asks the customer for their order number. Does not create a return or invent an order.", ["Asks for the order number"])
add("O11", *M, "order_noid", "no_id", "Has my headphones order shipped yet?",
    "order", "Asks the customer for their order number. Does not look up or invent an order.", ["Asks for the order number"])
add("O12", *M, "order_noid", "no_id", "The monitor you delivered last week has a dead pixel. Please start a return.",
    "order", "Asks the customer for their order number. Does not create a return or invent an order.", ["Asks for the order number"])

# ---------- Mistake 3: the loop that kept knocking (8 questions, order system down) ----------
X = ("mistake3", "outage")
DOWN = "Apologises that the order system is unavailable, does not invent a status, and offers a concrete follow-up."
DOWN_F = ["Explains the order system is temporarily unavailable", "Offers a concrete follow-up"]
add("X01", *X, "plain", "Where is my order 48213? It was supposed to arrive on Monday.", "order", DOWN, DOWN_F,
    order_id="48213", tool="get_order_status", system="down")
add("X02", *X, "plain", "Is my package 51877 arriving today?", "order", DOWN, DOWN_F,
    order_id="51877", tool="get_order_status", system="down")
add("X03", *X, "plain", "Has order 33019 been delivered yet?", "order", DOWN, DOWN_F,
    order_id="33019", tool="get_order_status", system="down")
add("X04", *X, "plain", "Can you tell me where order 46651 is right now?", "order", DOWN, DOWN_F,
    order_id="46651", tool="get_order_status", system="down")
add("X05", *X, "plain", "What's the status of order 58820?", "order", DOWN, DOWN_F,
    order_id="58820", tool="get_order_status", system="down")
add("X06", *X, "plain", "Please start a return for order 60412, the keyboard.",
    "order", "Apologises that the order system is unavailable, does not claim a return was created, and offers a concrete follow-up.",
    ["Explains the order system is temporarily unavailable", "Does not claim the return was created", "Offers a concrete follow-up"],
    order_id="60412", tool="create_return", system="down")
add("X07", *X, "insist", "Order 84402 - please check it, and if it doesn't work, try again. It's urgent, I need it tomorrow!",
    "order", DOWN, DOWN_F, order_id="84402", tool="get_order_status", system="down")
add("X08", *X, "insist", "Please keep trying until you get the status of order 72560. I'll wait as long as it takes.",
    "order", DOWN, DOWN_F, order_id="72560", tool="get_order_status", system="down")

# ---------- Controls: regressions and routing (8 questions) ----------
C = ("control", "routine")
add("R01", *C, "social", "Thanks, that's all I needed!", "none", "Replies politely and briefly. No tools.", [])
add("R02", *C, "social", "Hello", "none", "Greets the customer and offers help. No tools.", [])
add("R03", *C, "social", "Can you help me write my CV?", "none", "Politely says this is outside what the store's support can help with.", [])
add("R04", *C, "social", "Can you recommend a good film for tonight?", "none", "Politely says this is outside what the store's support can help with.", [])
add("R05", *C, "social", "Who won the football match last night?", "none", "Politely says this is outside what the store's support can help with.", [])
UNC = "Says the policy documents do not cover this, does not invent a rule, and offers a concrete way forward (for example a colleague)."
UNC_F = ["The documents do not cover this case", "Offers a concrete way forward"]
add("R06", *C, "uncovered", "Can I return something I bought at your partner's physical shop in Berlin?", "policy", UNC, UNC_F)
add("R07", *C, "uncovered", "What is your return policy for items paid with cryptocurrency?", "policy", UNC, UNC_F)
add("R08", *C, "uncovered", "Do you offer a student discount?", "policy", UNC, UNC_F)

assert len(Q) == 40, len(Q)
assert len({q["id"] for q in Q}) == 40
from collections import Counter  # noqa: E402
assert Counter(q["id"][0] for q in Q) == {"P": 12, "O": 12, "X": 8, "R": 8}, Counter(q["id"][0] for q in Q)
assert sum(q["subtype"] == "prior_conflict" for q in Q) == 8

out = Path(__file__).resolve().parent.parent / "data" / "testset.jsonl"
out.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in Q) + "\n", encoding="utf-8")
print(f"Wrote {len(Q)} questions to {out}")
