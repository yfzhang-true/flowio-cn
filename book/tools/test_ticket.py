import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ticket
def test_new_and_report(tmp="book/tickets"):
    t = ticket.new("A205", "WS2812 状态灯", phase="hw", bringup="5.1", book_ch=11, root=".")
    assert t["status"] == "pending" and os.path.isfile("book/tickets/A205.yaml")
    rep = ticket.report(root=".")
    assert any(l.startswith("A205") and "pending" in l for l in rep.splitlines())
if __name__ == "__main__":
    import shutil; shutil.rmtree("book/tickets", ignore_errors=True)
    test_new_and_report(); shutil.rmtree("book/tickets", ignore_errors=True)
    print("ticket tests OK")
