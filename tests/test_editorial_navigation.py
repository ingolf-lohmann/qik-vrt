# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate the same permanent publication navigation in Site/public or Repo/docs."""
from __future__ import annotations
import hashlib
from html.parser import HTMLParser
import json
import os
import re
import struct
from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONTENT = Path(os.environ.get('QIKVRT_EDITORIAL_ROOT', str(ROOT / ('public' if (ROOT / 'public/news/topics.json').is_file() else 'docs')))).resolve()
BINDING = ROOT / 'state/work_units/QIKVRT_EDITORIAL_TOPICS_ALIGNMENT_20261012_V1.json'
EXPECTED_TOPICS = {'zutrittskontrolle', 'kuenstliche-intelligenz', 'physik'}
CLASSES = {'TECHNICAL_RESULT', 'FORMAL_MODEL_RESULT', 'SCIENTIFIC_HYPOTHESIS', 'EDITORIAL_INTERPRETATION', 'NORMATIVE_SOURCE'}

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links, self.sources, self.canonical = [], [], {}, None
        self.current_source = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href')
        if attrs.get('data-publication-source'):
            sid = attrs['data-publication-source']
            assert sid not in self.sources, 'duplicate source display'
            self.sources[sid] = {'class': attrs.get('data-evidence-class'), 'text': ''}
            self.current_source = sid

    def handle_endtag(self, tag):
        if tag == 'article':
            self.current_source = None

    def handle_data(self, data):
        if self.current_source:
            self.sources[self.current_source]['text'] += data


def validate(content: Path, binding: dict, project_root: Path = ROOT):
    home = Page((content / 'index.html').read_text())
    news = Page((content / 'news/index.html').read_text())
    manifest = json.loads((content / 'news/topics.json').read_text())
    topics = manifest['topics']
    assert len(topics) == 3 and {t['id'] for t in topics} == EXPECTED_TOPICS
    assert len(news.ids) == len(set(news.ids)), 'duplicate anchor'
    assert news.canonical == 'https://raumzeitterminal.de/news/'
    home_targets = {urlsplit(urljoin('https://example.invalid/', h)).path + ('#' + urlsplit(h).fragment if urlsplit(h).fragment else '') for h in home.links}
    assert '/news/' in home_targets, 'missing homepage news navigation'
    for topic in topics:
        assert topic['permanent'] is True
        assert topic['href'] == '/news/#' + topic['id']
        assert topic['id'] in news.ids, 'missing topic target'
        assert topic['href'] in home_targets, 'missing homepage topic link'
        assert '#' + topic['id'] in news.links, 'missing topic menu link'
    for href in news.links:
        target = urlsplit(urljoin('https://example.invalid/news/', href))
        if target.hostname != 'example.invalid':
            continue
        path = content / target.path.lstrip('/')
        if target.path.endswith('/'):
            path /= 'index.html'
        assert path.is_file(), f'broken local link: {href}'
        if target.fragment:
            assert target.fragment in Page(path.read_text()).ids, f'broken fragment: {href}'
    assert set(manifest['evidence_classes']) == CLASSES
    source_ids = [s['id'] for s in manifest['publication_sources']]
    assert len(source_ids) == len(set(source_ids)), 'duplicate publication source'
    assert set(source_ids) == set(news.sources), 'source visibility mismatch'
    assigned_sources = [sid for t in topics for sid in t['publication_source_ids']]
    assert sorted(assigned_sources) == sorted(source_ids), 'missing or repeated source assignment'
    for source in manifest['publication_sources']:
        display = news.sources[source['id']]
        assert source['evidence_class'] in CLASSES
        assert display['class'] == source['evidence_class'], 'evidence class mismatch'
        assert manifest['evidence_classes'][source['evidence_class']] in display['text'], 'hidden evidence label'
        assert source['scope'] in display['text'], 'hidden scope boundary'
        assert source['record_url'] in display['text'] and source['record_url'] in news.links, 'hidden source URL'
        assert source['doi'] in display['text'] and 'https://doi.org/' + source['doi'] in news.links, 'hidden DOI'
        assert source['evidence_boundary'], 'missing archival boundary'
        assert source['publication_date'] in display['text'], 'hidden source publication date'
        assert source['version'] in display['text'], 'hidden source version'
    for key in ['html', 'json']:
        assert manifest['publication_index'][key] in news.links, 'missing publication atlas navigation'
    # Repository atlas navigation must point back to each existing topic.
    atlas_path = content / 'publications/index.html'
    if atlas_path.is_file():
        atlas_page = Page(atlas_path.read_text())
        for topic in topics:
            assert '../news/#' + topic['id'] in atlas_page.links, 'missing atlas topic return link'
        atlas_metadata = json.loads((content / 'publications/index.json').read_text())
        assert set(atlas_metadata['editorial_navigation']['topic_ids']) == EXPECTED_TOPICS
        assert '../news/' in atlas_page.links and '../news/topics.json' in atlas_page.links
    articles = manifest['articles']
    ids = [a['id'] for a in articles]
    assert len(ids) == len(set(ids)), 'duplicate article identity'
    assert len({a['canonical_url'] for a in articles}) == len(articles), 'duplicate canonical article'
    assert sorted(aid for t in topics for aid in t['article_ids']) == sorted(ids), 'inconsistent article assignment'
    actual_metadata = {p.parent.name for p in (content / 'news').glob('*/index.json')}
    assert actual_metadata == set(ids), 'unindexed or duplicate article page'
    for article in articles:
        metadata_file = content / 'news' / article['metadata_href']
        metadata = json.loads(metadata_file.read_text())
        assert hashlib.sha256(metadata_file.read_bytes()).hexdigest() == article['metadata_sha256'], 'article metadata changed'
        for key in ['id', 'date', 'classification', 'canonical_url', 'languages', 'variants']:
            assert article[key] == metadata[key], 'article index metadata drift: ' + key
        assert article['title'] == metadata['title_de']
        assert article['href'] in news.links and article['metadata_href'] in news.links
        assert Page((content / 'news' / article['href'] / 'index.html').read_text()).canonical == metadata['canonical_url']
    # Audit links from the retained articles too, including their historical atlas URL.
    for article in articles:
        base = 'https://example.invalid/news/' + article['href']
        article_page = Page((content / 'news' / article['href'] / 'index.html').read_text())
        for href in article_page.links:
            target = urlsplit(urljoin(base, href))
            if target.hostname != 'example.invalid':
                continue
            path = content / target.path.lstrip('/')
            if target.path.endswith('/'):
                path /= 'index.html'
            if not path.is_file() and target.path.rstrip('/') == '/publications':
                assert manifest['publication_index']['local_alias'] == '/publications/'
                route = project_root / 'app/publications/route.ts'
                assert route.is_file(), 'missing historical publication-index alias'
                assert manifest['publication_index']['html'] in route.read_text(), 'publication alias target drift'
                continue
            assert path.is_file(), f'broken retained article navigation: {href}'
            if target.fragment:
                assert target.fragment in Page(path.read_text()).ids, 'broken retained article fragment'
    for relative, expected in binding['preserved_article_files'].items():
        data = (content / relative).read_bytes()
        assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256'], 'frozen article bytes changed: ' + relative
    return manifest


class EditorialNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding = json.loads(BINDING.read_text())

    def fixture(self, directory):
        path = Path(directory)
        shutil.copytree(CONTENT / 'news', path / 'news')
        shutil.copy2(CONTENT / 'index.html', path / 'index.html')
        if (CONTENT / 'publications').is_dir():
            shutil.copytree(CONTENT / 'publications', path / 'publications')
        elif (ROOT / 'app/publications').is_dir():
            shutil.copytree(ROOT / 'app/publications', path / 'app/publications')
        if (CONTENT / 'terminal').is_dir():
            shutil.copytree(CONTENT / 'terminal', path / 'terminal')
        return path

    def bad_manifest(self, change):
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory)
            file = path / 'news/topics.json'
            manifest = json.loads(file.read_text())
            change(manifest)
            file.write_text(json.dumps(manifest))
            with self.assertRaises((AssertionError, KeyError, FileNotFoundError)):
                validate(path, self.binding, path)

    def test_live_source_navigation_metadata_and_frozen_bytes(self):
        validate(CONTENT, self.binding)

    def test_missing_topic_target_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory)
            file = path / 'news/index.html'
            file.write_text(file.read_text().replace('id="physik"', 'id="other"'))
            with self.assertRaises(AssertionError):
                validate(path, self.binding, path)

    def test_evidence_class_inflation_rejected(self):
        self.bad_manifest(lambda m: m['publication_sources'][0].update(evidence_class='EMPIRICALLY_CONFIRMED'))

    def test_duplicate_publication_source_rejected(self):
        self.bad_manifest(lambda m: m['publication_sources'].append(m['publication_sources'][0]))

    def test_duplicate_article_identity_rejected(self):
        self.bad_manifest(lambda m: m['articles'].append(m['articles'][0]))

    def test_article_metadata_drift_rejected(self):
        self.bad_manifest(lambda m: m['articles'][0].update(date='2000-01-01'))

    def test_missing_atlas_link_rejected(self):
        self.bad_manifest(lambda m: m['publication_index'].update(html='https://example.invalid/missing-atlas'))

    def test_source_class_mismatch_rejected(self):
        self.bad_manifest(lambda m: m['publication_sources'][1].update(evidence_class='SCIENTIFIC_HYPOTHESIS'))

    def test_missing_article_atlas_destination_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory)
            for target in [path / 'publications', path / 'app/publications']:
                if target.is_dir():
                    shutil.rmtree(target)
            with self.assertRaises((AssertionError, KeyError)):
                validate(path, self.binding, path)

    def test_frozen_article_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.fixture(directory)
            file = path / 'news/universaler-transputer/article.txt'
            file.write_bytes(file.read_bytes() + b'changed')
            with self.assertRaises(AssertionError):
                validate(path, self.binding, path)


def validate_poetic_homepage(content: Path, binding: dict):
    """Preserve source content and navigation, independent of a hosted service."""
    root = content.parent
    for entry in binding['originals']:
        data = (root / entry['path']).read_bytes()
        assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], 'original bytes changed'
    original = (content / 'texte/La_mere_bien_sur_57_Uebersetzungen.html').read_text()
    collection = (content / 'sprachen.html').read_text()
    articles = lambda text: re.findall(r'<article id="([^"]+)">(.*?)</article>', text, re.S)
    source_articles = articles(original)
    assert len(source_articles) == 58 and len({key for key, _ in source_articles}) == 58
    assert articles(collection) == source_articles, 'language content or order changed'
    assert {key for key, _ in source_articles} == set(Page(collection).ids) - {'languages'}
    assert {'fr','de','en','ru','ar','zh-Hans','es','pt','tr','uk','pl'} <= {key for key, _ in source_articles}
    assert 'lang="ar" dir="rtl"' in collection and 'lang="yi" dir="rtl"' in collection
    assert './' in Page(collection).links, 'missing collection return path'

    class Text(HTMLParser):
        def __init__(self, text):
            super().__init__(); self.parts = []; self.feed(text)
        def handle_data(self, data): self.parts.append(data)
        def normalized(self): return ' '.join(' '.join(self.parts).split())
    german = dict(source_articles)['de']
    poem = re.search(r'<div class="poem"[^>]*>(.*?)</div>', german, re.S).group(1)
    signature = re.search(r'<p class="signature"[^>]*>(.*?)</p>', german, re.S).group(1)
    expected = Text(poem + signature).normalized()
    assert Text((content / 'texte/la-mere-deutsch.txt').read_text()).normalized() == expected, 'German download drift'
    home = (content / 'index.html').read_text()
    displayed = re.search(r'<p class="opening-question">(.*?)<div class="poem-actions">', home, re.S).group(1)
    assert Text(displayed).normalized() == expected, 'German homepage drift'
    assert '<html lang="de">' in home and home.index('id="gedicht"') < home.index('id="sprachen"')
    assert 'width="1024" height="1536" alt="' in home
    image = (content / 'assets/images/la-mere-bien-sur.png').read_bytes()
    assert image[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', image[16:24]) == (1024,1536)
    page = Page(home)
    assert len(page.ids) == len(set(page.ids))
    for prefix in ['/', '/qik-vrt/']:
        base = 'https://source.invalid' + prefix
        for href in page.links:
            target = urlsplit(urljoin(base, href))
            if target.hostname != 'source.invalid': continue
            assert target.path.startswith(prefix), 'homepage link escaped hosting prefix'
            path = content / target.path[len(prefix):]
            if target.path.endswith('/'): path /= 'index.html'
            assert path.is_file(), f'broken homepage link: {href}'
            if target.fragment and target.fragment != '/':
                assert target.fragment in Page(path.read_text()).ids, f'broken homepage fragment: {href}'
    assert 'https://qikvrt-scheibenhard.ingolf-lohmann.chatgpt.site/release/index.html' in page.links
    assert {'terminal/','news/','publications/index.html','monitor/#/','monitor/offline/','projekt.html'} <= set(page.links)
    project = (content / 'projekt.html').read_text()
    reconstructed = project.replace('\n      <a href="./">Startseite</a>', '')
    assert hashlib.sha256(reconstructed.encode()).hexdigest() == binding['preserved_project']['predecessor_sha256'], 'legacy project changed'
    assert {'konsole','timeline','produkt','audit','recht','wissenschaft','kontakt'} <= set(Page(project).ids)
    return len(source_articles)


class PoeticHomepageTests(unittest.TestCase):
    def setUp(self):
        self.binding = json.loads((ROOT / 'state/work_units/QIKVRT_POETIC_HOMEPAGE_SOURCE_20261018_V1.json').read_text())

    def test_originals_all_languages_german_poster_and_root_or_prefix_navigation(self):
        self.assertEqual(validate_poetic_homepage(CONTENT, self.binding), 58)

    def test_source_integration_does_not_claim_public_domain_or_republish(self):
        self.assertEqual(self.binding['published_site']['version_number'], 37)
        self.assertFalse(self.binding['published_site']['mutated_by_this_work'])
        for field in ['chatgpt_site_republished','dns_or_tls_changed','public_domain_delivery_verified','native_product_acceptance_inferred','effect_ack_done']:
            self.assertIs(self.binding['boundaries'][field], False)

    def reject_mutation(self, relative, mutate):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Read-only dependencies are links; only the deliberately damaged
            # file is copied, so every negative case retains the other checks.
            shutil.copytree(CONTENT, root / 'docs', symlinks=True, copy_function=lambda src,dst: os.symlink(src,dst))
            (root / 'state').symlink_to(ROOT / 'state', target_is_directory=True)
            target = root / 'docs' / relative
            raw = target.read_bytes(); target.unlink(); target.write_bytes(mutate(raw))
            with self.assertRaises((AssertionError, AttributeError)):
                validate_poetic_homepage(root / 'docs', self.binding)

    def test_lost_language_is_rejected(self):
        self.reject_mutation('sprachen.html', lambda b:b.replace(b'<article id="uk">', b'<article id="missing">'))

    def test_changed_original_image_is_rejected(self):
        self.reject_mutation('assets/images/la-mere-bien-sur.png', lambda b:b[:-1] + bytes([b[-1] ^ 1]))

    def test_german_text_drift_is_rejected(self):
        self.reject_mutation('index.html', lambda b:b.replace('Die Mutter,'.encode(), 'Der Vater,'.encode()))

    def test_broken_navigation_is_rejected(self):
        self.reject_mutation('index.html', lambda b:b.replace(b'href="terminal/"', b'href="absent/"'))


if __name__ == '__main__':
    unittest.main()
