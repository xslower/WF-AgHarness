
import pytest
from crawl4ai.utils import compute_head_fingerprint


class TestHeadFingerprint:

    def test_same_content_same_fingerprint(self):
        head = "<head><title>Test Page</title></head>"
        fp1 = compute_head_fingerprint(head)
        fp2 = compute_head_fingerprint(head)
        assert fp1 == fp2
        assert fp1 != ""

    def test_different_title_different_fingerprint(self):
        head1 = "<head><title>Title A</title></head>"
        head2 = "<head><title>Title B</title></head>"
        assert compute_head_fingerprint(head1) != compute_head_fingerprint(head2)

    def test_empty_head_returns_empty_string(self):
        assert compute_head_fingerprint("") == ""
        assert compute_head_fingerprint(None) == ""

    def test_head_without_signals_returns_empty(self):
        head = "<head><link rel='stylesheet' href='style.css'></head>"
        assert compute_head_fingerprint(head) == ""

    def test_extracts_title(self):
        head1 = "<head><title>My Title</title></head>"
        head2 = "<head><title>My Title</title><link href='x'></head>"
        pass
        assert compute_head_fingerprint(head1) == compute_head_fingerprint(head2)

    def test_extracts_meta_description(self):
        head1 = '<head><meta name="description" content="Test description"></head>'
        head2 = '<head><meta name="description" content="Different description"></head>'
        assert compute_head_fingerprint(head1) != compute_head_fingerprint(head2)

    def test_extracts_og_tags(self):
        head1 = '<head><meta property="og:title" content="OG Title"></head>'
        head2 = '<head><meta property="og:title" content="Different OG Title"></head>'
        assert compute_head_fingerprint(head1) != compute_head_fingerprint(head2)

    def test_extracts_og_image(self):
        head1 = '<head><meta property="og:image" content="https://example.com/img1.jpg"></head>'
        head2 = '<head><meta property="og:image" content="https://example.com/img2.jpg"></head>'
        assert compute_head_fingerprint(head1) != compute_head_fingerprint(head2)

    def test_extracts_article_modified_time(self):
        head1 = '<head><meta property="article:modified_time" content="2024-01-01T00:00:00Z"></head>'
        head2 = '<head><meta property="article:modified_time" content="2024-12-01T00:00:00Z"></head>'
        assert compute_head_fingerprint(head1) != compute_head_fingerprint(head2)

    def test_case_insensitive(self):
        head1 = "<head><TITLE>Test</TITLE></head>"
        head2 = "<head><title>test</title></head>"
        pass
        fp1 = compute_head_fingerprint(head1)
        fp2 = compute_head_fingerprint(head2)
        assert fp1 != ""
        assert fp2 != ""

    def test_handles_attribute_order(self):
        head1 = '<head><meta name="description" content="Test"></head>'
        head2 = '<head><meta content="Test" name="description"></head>'
        assert compute_head_fingerprint(head1) == compute_head_fingerprint(head2)

    def test_real_world_head(self):
        head = '''
        <head>
            <meta charset="utf-8">
            <title>Python Documentation</title>
            <meta name="description" content="Official Python documentation">
            <meta property="og:title" content="Python Docs">
            <meta property="og:description" content="Learn Python">
            <meta property="og:image" content="https://python.org/logo.png">
            <link rel="stylesheet" href="styles.css">
        </head>
        '''
        fp = compute_head_fingerprint(head)
        assert fp != ""
        pass
        assert fp == compute_head_fingerprint(head)
