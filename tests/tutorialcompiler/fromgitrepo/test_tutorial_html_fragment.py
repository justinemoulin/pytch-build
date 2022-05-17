import pytest
from dataclasses import dataclass
from typing import List
from bs4 import BeautifulSoup

import pytchbuild.tutorialcompiler.fromgitrepo.tutorial_history as TH
import pytchbuild.tutorialcompiler.fromgitrepo.tutorial_html_fragment as THF


@dataclass
class MockHunkLine:
    old_lineno: int
    new_lineno: int
    content: str


@dataclass
class MockHunk:
    lines: List[MockHunkLine]


@dataclass
class MockPatch:
    hunks: List[MockHunk]


@pytest.fixture
def soup():
    return BeautifulSoup('', 'html.parser')


class TestHunkTable:
    @pytest.mark.parametrize(
        'old_lineno,new_lineno,exp_class',
        [
            (10, 12, 'diff-unch'),
            (-1, 8, 'diff-add'),
            (12, -1, 'diff-del')
        ])
    def test_line_classification(self, old_lineno, new_lineno, exp_class):
        mock_hunk_line = MockHunkLine(old_lineno, new_lineno, 'ignored')
        got_class = THF.line_classification(mock_hunk_line)
        assert got_class == exp_class

    @pytest.mark.parametrize(
        'lineno,exp_html',
        [
            (-1, '<td class="linenum"></td>'),
            (10, '<td class="linenum"><pre>10</pre></td>'),
        ])
    def test_table_data_from_line_number(self, soup, lineno, exp_html):
        got_html = THF.table_data_from_line_number(soup, lineno)
        assert str(got_html) == exp_html

    def test_table_row_from_line(self, soup):
        line = MockHunkLine(10, 12, 'foo()')
        got_html = THF.table_row_from_line(soup, line)
        assert str(got_html) == (
            '<tr>'
            '<td class="linenum"><pre>10</pre></td>'
            '<td class="linenum"><pre>12</pre></td>'
            '<td><pre>foo()</pre></td></tr>'
        )

    def test_table_from_hunk(self, soup):
        hunk = MockHunk([
            MockHunkLine(10, 12, 'foo()\n'),
            MockHunkLine(11, -1, 'bar()\n'),
        ])
        got_html = THF.table_from_hunk(soup, hunk)
        assert str(got_html) == (
            '<table>'
            '<tbody class="diff-unch">'
            '<tr>'
            '<td class="linenum"><pre>10</pre></td>'
            '<td class="linenum"><pre>12</pre></td>'
            '<td><pre>foo()</pre></td></tr>'
            '</tbody>'
            '<tbody class="diff-del">'
            '<tr>'
            '<td class="linenum"><pre>11</pre></td>'
            '<td class="linenum"></td>'
            '<td><pre>bar()</pre></td></tr>'
            '</tbody>'
            '</table>'
        )

    def test_tables_div_from_patch(self, soup):
        patch = MockPatch([
            MockHunk([
                MockHunkLine(10, 12, 'foo()\n'),
                MockHunkLine(11, -1, 'bar()\n'),
            ]),
            MockHunk([
                MockHunkLine(-1, 22, 'baz()\n'),
                MockHunkLine(-1, 23, 'baz2()\n'),
                MockHunkLine(24, 24, 'qux()\n'),
            ]),
        ])
        got_html = THF.tables_div_from_patch(soup, patch)
        assert str(got_html) == (
            '<div class="patch">'
            '<table>'
            '<tbody class="diff-unch">'
            '<tr>'
            '<td class="linenum"><pre>10</pre></td>'
            '<td class="linenum"><pre>12</pre></td>'
            '<td><pre>foo()</pre></td></tr>'
            '</tbody>'
            '<tbody class="diff-del">'
            '<tr>'
            '<td class="linenum"><pre>11</pre></td>'
            '<td class="linenum"></td>'
            '<td><pre>bar()</pre></td></tr>'
            '</tbody>'
            '</table>'
            '<table>'
            '<tbody class="diff-add" data-added-text="baz()\nbaz2()\n">'
            '<tr>'
            '<td class="linenum"></td>'
            '<td class="linenum"><pre>22</pre></td>'
            '<td><pre>baz()</pre></td></tr>'
            '<tr>'
            '<td class="linenum"></td>'
            '<td class="linenum"><pre>23</pre></td>'
            '<td><pre>baz2()</pre></td></tr>'
            '</tbody>'
            '<tbody class="diff-unch">'
            '<tr>'
            '<td class="linenum"><pre>24</pre></td>'
            '<td class="linenum"><pre>24</pre></td>'
            '<td><pre>qux()</pre></td></tr>'
            '</tbody>'
            '</table>'
            '</div>'
        )


class TestHtmlFragment:
    @staticmethod
    def paragraph(soup, text):
        p = soup.new_tag("p")
        p.append(text)
        return p

    def test_div_from_chapter(self, soup):
        chapter = [
            self.paragraph(soup, "hello"),
            self.paragraph(soup, "world"),
        ]
        assert str(THF.div_from_chapter(soup, chapter)) == (
            '<div class="chapter-content">'
            '<p>hello</p>'
            '<p>world</p>'
            '</div>'
        )

    @pytest.mark.parametrize("wip_idx", [None, 3])
    def test_div_from_front_matter(self, soup, wip_idx):
        front_matter = [
            self.paragraph(soup, "hello"),
            self.paragraph(soup, "world"),
        ]
        code_0 = 'bar()'
        code = 'foo()'

        # It's possible this will fail one day if I'm making unwarranted
        # assumptions about the order in which attributes are represented
        # in the string form of an HTML fragment.

        got_div = THF.div_from_front_matter(soup, front_matter, wip_idx, code_0, code)
        assert str(got_div) == (
            '<div class="front-matter"'
            ' data-complete-code-text="foo()"'
            ' data-initial-code-text="bar()"'
            '{}'
            '>'
            '<p>hello</p>'
            '<p>world</p>'
            '</div>'.format(' data-seek-to-chapter="3"' if wip_idx
                            else "")
        )

    def test_work_in_progress_marker(self, project_history):
        got_div = THF.tutorial_div_from_project_history(project_history)
        front_matter = got_div.find("div", class_="front-matter")
        if project_history.tutorial_text.startswith("Working copy"):
            assert "data-seek-to-chapter" not in front_matter.attrs
        else:
            assert front_matter.attrs["data-seek-to-chapter"] == "2"

    def test_asset_credits_shortcode(self, project_history):
        # This test only applies to committed version of content:
        TTS = TH.ProjectHistory.TutorialTextSource
        if project_history.tutorial_text_source != TTS.TIP_REVISION:
            return

        div = THF.tutorial_div_from_project_history(project_history)

        front_matter_credits = (
            div
            .find("div", class_="front-matter")
            .find_all("p", class_="credit-intro")
        )
        assert len(front_matter_credits) == 1

        # Find credit-intro elts within final chapter:
        body_credits = (
            div
            .find_all("div", class_="chapter-content")[-1]
            .find_all("p", class_="credit-intro")
        )
        assert len(body_credits) == 1


class TestPredicates:
    @pytest.mark.parametrize(
        'html,exp_is_relevant',
        [
            pytest.param('<p>Hello</p>', True, id="P-element"),
            pytest.param('   Hello', True, id="string-leading-spaces"),
            pytest.param('Hello       ', True, id="string-trailing-spaces"),
            pytest.param('    ', False, id="string-nonempty-all-spaces"),
            pytest.param('\n\nfoo\n', True, id="string-leading-trailing-NLs"),
        ])
    def test_node_is_relevant(self, html, exp_is_relevant):
        soup = BeautifulSoup(html, "html.parser")
        node = next(soup.children)
        assert THF.node_is_relevant(node) == exp_is_relevant

    @pytest.mark.parametrize(
        'html,exp_is_patch',
        [
            ('<p>Hello</p>', False),
            ('<div><p>Hello</p></div>', False),
            ('<div class="banana"><p>Hello</p></div>', False),
            ('<div class="patch-container"><p>Hello</p></div>', True),
            ('<div class="patch-container banana"><p>Hello</p></div>', True),
        ])
    def test_node_is_patch(self, html, exp_is_patch):
        soup = BeautifulSoup(html, "html.parser")
        node = next(soup.children)
        assert THF.node_is_patch(node) == exp_is_patch
