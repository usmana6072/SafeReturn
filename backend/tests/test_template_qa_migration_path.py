"""The QA deployment path must not transit the protected Support migration."""
import hashlib
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_qa_upgrade_excludes_protected_support_revision():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    script = ScriptDirectory.from_config(config)
    path = list(script.iterate_revisions('0050_public_catalog_browsing', '0043_standalone_activation'))
    assert [revision.revision for revision in path] == ['0050_public_catalog_browsing', '0049_manual_approval_attach', '0048_manual_template_binding', '0047_qa_auto_publication', '0046_manual_template_qa', '0045_template_qa_reviews']
    assert 'template_qa' in script.get_revision('0045_template_qa_reviews').branch_labels
    assert script.get_revision('0044_support_dev_exception').down_revision == '0043_standalone_activation'
    expected = {'sql': '17b3b5bd5964f6dfb7a1b610bce455d32fc805539282e3ecb7d79a9e39a19a2d', 'py': '67318373a9fecdca0fa441697d37ae4a1c0719d7ce0dd1e125e85ea07ddc5c30'}
    for extension, digest in expected.items():
        assert hashlib.sha256((root / f'alembic/versions/0044_support_dev_exception.{extension}').read_bytes()).hexdigest() == digest
