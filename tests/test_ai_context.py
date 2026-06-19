import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zxtp.ai_context import generate_full_context
from zxtp.tqlex import RawCacheWriter


class AiContextGenerationTests(unittest.TestCase):
    def test_generates_stock_first_markdown_with_stable_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            writer = RawCacheWriter(data_root)
            writer.write(
                entry="tdxf10_gg_gsgk",
                params=["0", "002736", ""],
                stock_code="002736",
                module="gsgk",
                source_url="http://example.test/TQLEX?Entry=CWServ.tdxf10_gg_gsgk",
                json_data={"ErrorCode": 0, "ResultSets": [], "ResultSetNum": 0},
            )

            output_path = generate_full_context("002736", data_root)

            self.assertEqual(
                output_path,
                data_root / "exports" / "ai_context" / "002736" / "full_context.md",
            )
            text = output_path.read_text(encoding="utf-8")
            self.assertIn('stock_code: "002736"', text)
            self.assertIn("# 002736 研究上下文", text)
            self.assertIn("## 1. 基本信息", text)
            self.assertIn("## 2. 公司概况", text)
            self.assertIn("## 3. 财务分析", text)
            self.assertIn("## 4. 研报评级", text)
            self.assertIn("## 5. 行业分析", text)
            self.assertIn("## 6. 风险与待验证问题", text)
            self.assertIn("## 7. 数据来源", text)
            self.assertIn("tdxf10_gg_gsgk", text)
            self.assertIn("module=gsgk", text)
            self.assertIn("tdxf10_gg_cwfx", text)
            self.assertIn("tdxf10_gg_hyfx", text)
            self.assertIn("缺失", text)


if __name__ == "__main__":
    unittest.main()
