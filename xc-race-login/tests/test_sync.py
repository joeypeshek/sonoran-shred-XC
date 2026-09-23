import copy
import json
import unittest
from scripts.sync_bikereg import extract, merge, build, SEED, ROOT, IDS

class SyncTests(unittest.TestCase):
    def response(self):
        cats = [dict(raceRecId=str(i), eventEntries=[]) for i in sorted(IDS)]
        cats[0]['eventEntries'] = [dict(firstName='New', lastName='Rider', teamName='UA Cycling', entryDate=''),dict(firstName='Review',lastName='Rider',teamName='Arizona Wildcats',entryDate=''),dict(firstName='Other',lastName='Rider',teamName='Arizona State',entryDate='')]
        return {'data':{'AR_EventCategories':cats}}

    def test_team_matching(self):
        result = extract(self.response())
        self.assertEqual([e['name'] for e in result['entries']], ['New Rider'])
        self.assertEqual([e['name'] for e in result['review']], ['Review Rider'])

    def test_incomplete_and_empty_fail(self):
        response = self.response()
        response['data']['AR_EventCategories'].pop()
        with self.assertRaises(ValueError): extract(response)
        response = self.response()
        response['data']['AR_EventCategories'][0]['eventEntries'] = []
        with self.assertRaises(ValueError): extract(response)

    def test_preserves_officer_data_and_adds_rider(self):
        html = (ROOT/'index.html').read_text()
        seed = json.loads(SEED.search(html)[2])
        original = copy.deepcopy(seed)
        result = merge(seed, extract(self.response()))
        for field in ('design','shifts','exportId'):
            self.assertEqual(result[field], seed[field])
        for member in seed['members']:
            self.assertIn(member, result['members'])
        self.assertEqual(seed, original)
        self.assertEqual(next(m for m in result['members'] if m['id']=='new rider')['volunteer'], 'none')

    def test_safe_embedded_json(self):
        html = (ROOT/'index.html').read_text()
        snapshot = extract(self.response())
        snapshot['entries'][0]['name'] = '</script><img>'
        output = build(html, snapshot)
        self.assertEqual(output.count('</script>'), html.count('</script>'))
        self.assertEqual(json.loads(SEED.search(output)[2])['entries'][0]['name'], '</script><img>')

if __name__ == '__main__': unittest.main()
