import json
from datetime import datetime

from app.errors import UpstreamError
from app.schemas import PdfBatchDownloadRequest
from app.services.pdf_service import (
    create_batch_directory,
    fetch_ruling_pdf,
    sanitize_product_name,
)


def test_safe_product_directory_and_separate_batches(tmp_path):
    now = datetime(2026, 7, 24, 12, 34, 56)
    first = create_batch_directory('../CON:<测试>. ', tmp_path, now)
    second = create_batch_directory('../CON:<测试>. ', tmp_path, now)

    assert tmp_path.resolve() in first.resolve().parents
    assert first.name == '20260724_123456'
    assert second.name == '20260724_123456_2'
    assert first.parent == second.parent
    assert all(char not in first.parent.name for char in '<>:"/\\|?*')
    assert sanitize_product_name('..') == '未命名产品'


def test_batch_request_has_no_case_count_limit():
    numbers = [f'N{index:05d}' for index in range(1001)]
    body = PdfBatchDownloadRequest(product_name='测试产品', ruling_numbers=numbers)
    assert len(body.ruling_numbers) == 1001


def test_fetch_ruling_pdf_uses_official_metadata(monkeypatch):
    payloads = iter([
        json.dumps({
            'rulingNumber': 'N353849',
            'collection': 'ny',
            'rulingDate': '2025-10-09T00:00:00',
        }).encode(),
        b'%PDF-1.4\nmock',
    ])
    urls = []

    class FakeResponse:
        def __init__(self, content):
            self.content = content

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return self.content

    def fake_urlopen(request, timeout):
        urls.append(request.full_url)
        return FakeResponse(next(payloads))

    monkeypatch.setattr('app.services.pdf_service.urllib.request.urlopen', fake_urlopen)
    assert fetch_ruling_pdf('n353849') == b'%PDF-1.4\nmock'
    assert urls == [
        'https://rulings.cbp.gov/api/ruling/N353849',
        'https://rulings.cbp.gov/api/getdoc/ny/2025/N353849.pdf',
    ]


def test_single_and_batch_pdf_endpoints(client, monkeypatch, tmp_path):
    from app.routers import rulings

    monkeypatch.setattr(rulings, 'REFERENCE_CASES_DIR', tmp_path)
    monkeypatch.setattr(
        rulings._db,
        'fetch_ruling_by_no',
        lambda number: {'ruling_no': number} if number == 'N12345' else None,
    )
    monkeypatch.setattr(rulings, 'fetch_ruling_pdf', lambda number: b'%PDF-1.4\nmock')

    single = client.get('/api/rulings/N12345/pdf')
    assert single.status_code == 200
    assert single.content.startswith(b'%PDF-')
    assert single.headers['content-type'] == 'application/pdf'
    assert 'N12345.pdf' in single.headers['content-disposition']

    batch = client.post('/api/rulings/download-pdfs', json={
        'product_name': '球类/玩具',
        'ruling_numbers': ['N12345', 'N12345', 'MISSING'],
    })
    assert batch.status_code == 200
    data = batch.json()['data']
    assert data['downloaded'] == ['N12345']
    assert data['failed'][0]['ruling_no'] == 'MISSING'
    saved_dir = tmp_path / '球类_玩具'
    batches = list(saved_dir.iterdir())
    assert len(batches) == 1
    assert (batches[0] / 'N12345.pdf').read_bytes().startswith(b'%PDF-')


def test_batch_returns_502_when_every_pdf_fails(client, monkeypatch, tmp_path):
    from app.routers import rulings

    monkeypatch.setattr(rulings, 'REFERENCE_CASES_DIR', tmp_path)
    monkeypatch.setattr(
        rulings._db,
        'fetch_ruling_by_no',
        lambda number: {'ruling_no': number},
    )

    def fail(_number):
        raise UpstreamError('failed')

    monkeypatch.setattr(rulings, 'fetch_ruling_pdf', fail)
    response = client.post('/api/rulings/download-pdfs', json={
        'product_name': '失败产品',
        'ruling_numbers': ['N12345'],
    })
    assert response.status_code == 502
    assert not list(tmp_path.rglob('*.pdf'))
