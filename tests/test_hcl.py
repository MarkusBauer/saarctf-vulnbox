import re

from tests.utils.cases import TestCase
from vulnbuild.config import GlobalConfig
from vulnbuild.hcl.parser import HclParser


class HclTests(TestCase):
    def _prepare_for_comparison(self, s: str) -> str:
        s = re.sub(r'#[^n]*\n', '\n', s)
        s = re.sub('\s+', '', s)
        s = s.replace(',]', ']').replace(',}', '}')
        return s

    def test_hcl_parser(self) -> None:
        for f in GlobalConfig.projects.rglob('*.pkr.hcl'):
            if f.name.startswith('temp-'):
                continue
            txt = f.read_text(encoding='utf-8')
            hcl = HclParser.parse(txt)
            txt2 = hcl.to_string()

            ctxt, ctxt2 = self._prepare_for_comparison(txt), self._prepare_for_comparison(txt2)
            if ctxt != ctxt2:
                x = min(i for i, (a, b) in enumerate(zip(ctxt, ctxt2)) if a != b)
                print('File:', f)
                print(x, repr(ctxt[x - 10:x + 10]), '// original')
                print(x, repr(ctxt2[x - 10:x + 10]), '// after parse+stringify')
            self.assertEqual(self._prepare_for_comparison(txt), self._prepare_for_comparison(txt2))

    def test_quotes(self) -> None:
        txt = r'''a = "a\b\\c\"d\ne"'''
        f = HclParser.parse(txt)
        print('\n', f)
        txt2 = f.to_string()
        self.assertEqual(txt, txt2)

    def test_quotes_2(self) -> None:
        txt = r'''a = "CMD [\"/sbin/init\"]"'''
        f = HclParser.parse(txt)
        print('\n', f)
        txt2 = f.to_string()
        self.assertEqual(txt, txt2)

    def test_quotes_3(self) -> None:
        txt = '''changes = ["EXPOSE 22", "CMD [\\"/sbin/init\\"]"]'''.strip()
        f = HclParser.parse(txt)
        print('\n', f)
        txt2 = f.to_string()
        self.assertEqual(txt, txt2)
