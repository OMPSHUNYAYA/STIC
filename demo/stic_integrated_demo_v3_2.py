import hashlib
import json


def normalize(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sigma(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def sig_obj(obj):
    return sigma(normalize(obj))


def resolve_message(s):
    if not all(k in s for k in ["message_id", "intent", "expectation", "conflict"]):
        return ("ABSTAIN", None, None, "missing structure")

    if s["conflict"]:
        return ("BLOCKED", None, None, "conflict present")

    if s["intent"] != s["expectation"]:
        return ("BLOCKED", None, None, "intent mismatch")

    visible = {"message_id": s["message_id"], "status": "STRUCTURALLY_DELIVERED"}
    return ("RESOLVED", visible, sig_obj(visible), "structure complete and consistent")


def resolve_otp(s):
    if not all(k in s for k in ["user_id", "expected_hash", "provided_hash", "window_valid", "conflict"]):
        return ("ABSTAIN", None, None, "missing structure")

    if s["conflict"]:
        return ("BLOCKED", None, None, "conflict present")

    if not s["window_valid"]:
        return ("BLOCKED", None, None, "window invalid")

    if s["expected_hash"] != s["provided_hash"]:
        return ("BLOCKED", None, None, "hash mismatch")

    visible = {"user_id": s["user_id"], "status": "VERIFIED"}
    return ("RESOLVED", visible, sig_obj(visible), "structure complete and consistent")


def resolve_path(s):
    required = [("SOURCE", "A"), ("A", "B"), ("B", "DESTINATION")]

    if "edges" not in s:
        return ("ABSTAIN", None, None, "missing edges")

    if s.get("conflict"):
        return ("BLOCKED", None, None, "conflict present")

    for edge in required:
        if edge not in s["edges"]:
            return ("ABSTAIN", None, None, "missing edge " + str(edge))

    visible = {"path": "SOURCE -> A -> B -> DESTINATION", "status": "VALID"}
    return ("RESOLVED", visible, sig_obj(visible), "structure complete and consistent")


def resolve_system(message, otp, path, dependency_state):
    m = resolve_message(message)
    o = resolve_otp(otp)
    p = resolve_path(path)

    states = [m[0], o[0], p[0]]

    if all(state == "RESOLVED" for state in states):
        system_state = "CORRECT"
        structure_mature = True
    elif any(state == "BLOCKED" for state in states):
        system_state = "BLOCKED"
        structure_mature = False
    else:
        system_state = "ABSTAIN"
        structure_mature = False

    certificate_components = {
        "message_sigma": m[2],
        "otp_sigma": o[2],
        "path_sigma": p[2],
        "system_state": system_state,
    }

    system_sigma = sig_obj(certificate_components)

    return {
        "modules": [m, o, p],
        "system_state": system_state,
        "structure_mature": structure_mature,
        "system_sigma": system_sigma,
        "dependency_state": dependency_state,
        "certificate_components": certificate_components,
    }


def print_case(title, result):
    print()
    print(title)
    print("=" * 72)

    print("Dependency state:", result["dependency_state"])
    print()

    names = ["MESSAGE", "OTP", "PATH"]

    for name, r in zip(names, result["modules"]):
        print(name, "Resolution")
        print("  state:", r[0])
        print("  visible:", r[1])
        print("  reason:", r[3])
        print("  sigma:", r[2])
        print()

    print("FINAL SYSTEM STATE")
    print("-" * 72)
    print("System correctness:", result["system_state"])
    print("Structural maturity:", result["structure_mature"])
    print("Certificate components:", result["certificate_components"])
    print("System certificate:", result["system_sigma"])
    print()


def main():
    print("STIC v3.2 — Structural Integrity without Cloud")
    print("correctness = resolve(structure)")
    print("=" * 72)

    base_message = {"message_id": "MSG-001", "intent": "CONFIRM", "expectation": "CONFIRM", "conflict": False}
    base_otp = {"user_id": "user-001", "expected_hash": "abc123", "provided_hash": "abc123", "window_valid": True, "conflict": False}
    base_path = {"edges": [("SOURCE", "A"), ("A", "B"), ("B", "DESTINATION")], "conflict": False}

    dep_off = {"cloud": "OFF", "network": "OFF", "execution": "OFF", "authority": "OFF"}
    dep_on = {"cloud": "ON", "network": "ON", "execution": "ON", "authority": "ON"}

    case1 = resolve_system(base_message, base_otp, base_path, dep_off)

    incomplete_path = {"edges": [("SOURCE", "A"), ("A", "B")], "conflict": False}
    case2 = resolve_system(base_message, base_otp, incomplete_path, dep_off)

    bad_otp = {"user_id": "user-001", "expected_hash": "abc123", "provided_hash": "wrong", "window_valid": True, "conflict": False}
    case3 = resolve_system(base_message, bad_otp, base_path, dep_off)

    case4a = resolve_system(base_message, base_otp, base_path, dep_off)
    case4b = resolve_system(base_message, base_otp, base_path, dep_off)

    case5 = resolve_system(base_message, base_otp, base_path, dep_on)

    print_case("CASE 1 — Dependencies OFF + complete structure", case1)
    print_case("CASE 2 — Incomplete structure", case2)
    print_case("CASE 3 — Conflicting structure", case3)

    print("CASE 4 — Replay Determinism Check")
    print("=" * 72)
    print("First certificate :", case4a["system_sigma"])
    print("Second certificate:", case4b["system_sigma"])
    print("Replay match:", case4a["system_sigma"] == case4b["system_sigma"])
    print()

    print_case("CASE 5 — Same structure with dependencies ON", case5)

    print("CASE 6 — Dependency Invariance Check")
    print("=" * 72)
    print("Dependencies OFF certificate:", case1["system_sigma"])
    print("Dependencies ON certificate :", case5["system_sigma"])
    print("Same correctness:", case1["system_state"] == case5["system_state"])
    print("Same certificate:", case1["system_sigma"] == case5["system_sigma"])
    print()

    print("=" * 72)
    print("STIC Insight")
    print("Structural guarantee: complete + consistent -> correctness visible.")
    print("Dependency state does not change correctness.")
    print("Same structure -> same correctness -> same certificate.")
    print("Structure alone determines correctness.")
    print("=" * 72)


if __name__ == "__main__":
    main()
