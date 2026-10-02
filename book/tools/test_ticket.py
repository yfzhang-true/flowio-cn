import sys, os, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import ticket
def test_new_and_report():
    # 沙箱 root：只操作临时目录，不触碰真实 book/tickets/（原版 rmtree 真目录曾误删 36 张工单）
    with tempfile.TemporaryDirectory() as td:
        t = ticket.new("A205", "WS2812 状态灯", phase="hw", bringup="5.1", book_ch=11, root=td)
        assert t["status"] == "pending" and os.path.isfile(os.path.join(td, "book/tickets/A205.yaml"))
        rep = ticket.report(root=td)
        assert any(l.startswith("A205") and "pending" in l for l in rep.splitlines())
if __name__ == "__main__":
    test_new_and_report()
    print("ticket tests OK")
