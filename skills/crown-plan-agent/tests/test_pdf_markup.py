"""Synthetic PDF review copies; never source plans or project artifacts."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
try:
    import pymupdf as fitz
except ImportError:
    fitz = None
try:
    from pdf_markup import build_annotated_pdf
except ModuleNotFoundError as exc:
    if exc.name != "pdf_markup":
        raise
    build_annotated_pdf = None
from pdf_inspector import extract_pdf
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory


@unittest.skipUnless(fitz is not None, "PyMuPDF unavailable")
class PDFMarkupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "invented.pdf"
        self.catalogue = [item for item in load_candidate_catalog(
            Path(__file__).resolve().parents[1] / "engine/candidate_requirements.json")
            if item["requirement_id"] == "CANDIDATE-PLAN-SCALE"]
        self.scenario = {"land_class": "alberta_crown", "regulator": "AER",
                         "disposition": "LOC", "stage": "initial", "plan_type": "sketch",
                         "purpose": "Invented purpose", "subactivity": "Invented activity"}

    def make_source(self, *, rotation=0, crop=False, unit=1, clipped=False,
                    repeated=False, graphics_only=False, existing=False):
        document = fitz.open()
        page = document.new_page(width=600, height=800)
        x, y, size = (-3 if clipped else 100), 160, 16
        if graphics_only:
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), False)
            pix.clear_with(220)
            page.insert_image(fitz.Rect(100, 100, 180, 180), pixmap=pix)
        else:
            page.insert_text((x, y), "SCALE 1:5000", fontsize=size)
            if repeated:
                page.insert_text((100, 220), "SCALE 1:5000", fontsize=size)
        if existing:
            old = page.add_rect_annot(fitz.Rect(430, 300, 470, 330))
            old.set_info(subject="Existing source comment", content="Keep this original note")
            old.set_colors(stroke=(0, 0, 1))
            old.update()
            page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(100, 400, 250, 420),
                              "uri": "https://example.invalid/original-source"})
            widget = fitz.Widget()
            widget.field_name = "original-field"
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_value = "Retained field"
            widget.rect = fitz.Rect(100, 450, 250, 475)
            page.add_widget(widget)
        bounds = (40, 60, 550, 720) if crop else (0, 0, 600, 800)
        page.set_cropbox(fitz.Rect(bounds))
        if unit != 1:
            document.xref_set_key(page.xref, "UserUnit", str(unit))
        page.set_rotation(rotation)
        document.save(self.source)
        document.close()
        font = fitz.Font("helv")
        visible = [max(0, (x-bounds[0])*unit), (y-font.ascender*size-bounds[1])*unit,
                   (x+font.text_length("SCALE 1:5000", fontsize=size)-bounds[0])*unit,
                   (y-font.descender*size-bounds[1])*unit]
        width, height = (bounds[2]-bounds[0])*unit, (bounds[3]-bounds[1])*unit
        if rotation == 0:
            expected = visible
        elif rotation == 90:
            expected = [height-visible[3], visible[0], height-visible[1], visible[2]]
        elif rotation == 180:
            expected = [width-visible[2], height-visible[3], width-visible[0], height-visible[1]]
        else:
            expected = [visible[1], width-visible[2], visible[3], width-visible[0]]
        return expected

    def report(self, *, catalogue=None):
        inventory = extract_pdf(self.source, include_vectors=False)
        report = review_inventory(inventory, self.scenario, catalogue or self.catalogue)
        return inventory, report

    def build(self, report, inventory, **kwargs):
        self.assertIsNotNone(build_annotated_pdf, "The PDF markup renderer is not implemented")
        return build_annotated_pdf(self.source, report, inventory, **kwargs)

    def assert_page_only_source_links(self, document, original_pages, expected_targets):
        """Verify PDF actions, since SDKs classify the same /Fit link differently."""
        source_xrefs={document.page_xref(i):i for i in range(original_pages)}
        targets=[]
        for page_number in range(original_pages,document.page_count):
            page=document[page_number]
            resolved={}
            link=page.load_links()
            while link is not None:
                resolved[link.xref]=document.resolve_link(link.uri)[0]
                link=link.next
            for xref,kind,_ in page.annot_xrefs():
                self.assertEqual(kind,fitz.PDF_ANNOT_LINK)
                self.assertEqual(document.xref_get_key(xref,'Subtype'),('name','/Link'))
                action_type,action=document.xref_get_key(xref,'A')
                self.assertEqual(action_type,'dict')
                match=re.fullmatch(r'<<\s*/S\s*/GoTo\s*/D\s*\[\s*(\d+)\s+0\s+R\s*/Fit\s*\]\s*>>',action)
                self.assertIsNotNone(match,'The entire action must be an internal page-only GoTo')
                target_xref=int(match.group(1))
                self.assertIn(target_xref,source_xrefs)
                target=source_xrefs[target_xref]
                self.assertEqual(resolved[xref],target)
                for extra in ('AA','Dest','URI'):
                    self.assertEqual(document.xref_get_key(xref,extra),('null','null'))
                targets.append(target)
        self.assertEqual(sorted(targets),sorted(expected_targets))

    def test_bytes_manifest_index_and_local_comment_are_complete(self):
        self.make_source()
        inventory, report = self.report()
        before_inventory, before_report = deepcopy(inventory), deepcopy(report)
        before = self.source.read_bytes()
        data, manifest = self.build(report, inventory)
        self.assertTrue(data.startswith(b"%PDF-"))
        self.assertEqual(manifest["source_sha256"], sha256(before).hexdigest())
        self.assertEqual(manifest["status"], "REVIEW_REQUIRED")
        self.assertEqual(manifest["original_page_count"], 1)
        self.assertGreaterEqual(manifest["notes_page_count"], 1)
        self.assertEqual(manifest["located_count"], 1)
        self.assertEqual(manifest["located_count"]+manifest["unlocated_count"], len(manifest["notes"]))
        with fitz.open(stream=data, filetype="pdf") as output:
            self.assertEqual(output.page_count, 1+manifest["notes_page_count"])
            source_page = output[0]
            comments = list(source_page.annots())
            self.assertEqual(len(comments), 1)
            self.assertIn("CANDIDATE-PLAN-SCALE", comments[0].info["content"])
            self.assertIn("REVIEW_REQUIRED", comments[0].info["content"])
            self.assertTrue(comments[0].flags & fitz.PDF_ANNOT_IS_PRINT)
            index = "\n".join(output[i].get_text() for i in range(1, output.page_count))
            self.assertIn(manifest["source_sha256"], index)
            for note in manifest["notes"]:
                self.assertIn(note["note_id"], index)
                self.assertIn(note["finding_id"], "".join(index.split()))
            self.assertIn("1.2.2.3", index)
            self.assert_page_only_source_links(output,1,[0])
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(inventory, before_inventory)
        self.assertEqual(report, before_report)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_source_content_frames_annotations_links_and_widgets_are_preserved(self):
        self.make_source(rotation=90, crop=True, unit=2, existing=True)
        inventory, report = self.report()
        data, manifest = self.build(report, inventory)
        with fitz.open(self.source) as source, fitz.open(stream=data, filetype="pdf") as output:
            left, right = source[0], output[0]
            self.assertEqual(list(left.mediabox), list(right.mediabox))
            self.assertEqual(list(left.cropbox), list(right.cropbox))
            self.assertEqual(left.rotation, right.rotation)
            self.assertEqual(left.get_text(), right.get_text())
            self.assertEqual(left.get_pixmap(annots=False).samples, right.get_pixmap(annots=False).samples)
            self.assertEqual(left.get_links(), right.get_links())
            old = list(left.annots())[0]
            retained = next(a for a in right.annots() if a.info["subject"] == "Existing source comment")
            self.assertEqual(old.info, retained.info)
            self.assertEqual(old.flags, retained.flags)
            self.assertEqual(list(old.rect), list(retained.rect))
            self.assertEqual([(w.field_name,w.field_value,list(w.rect)) for w in left.widgets()],
                             [(w.field_name,w.field_value,list(w.rect)) for w in right.widgets()])
            self.assert_page_only_source_links(output,1,[0])

    def test_visible_anchor_matches_rotated_cropped_unit_and_clipped_source(self):
        for rotation,crop,unit,clipped in ((0,False,1,False),(90,False,1,False),
                (180,False,1,False),(270,False,1,False),(0,True,1,False),
                (90,True,2,False),(270,True,2,False),(0,False,1,True)):
            with self.subTest(rotation=rotation,crop=crop,unit=unit,clipped=clipped):
                if self.source.exists(): self.source.unlink()
                expected = self.make_source(rotation=rotation,crop=crop,unit=unit,clipped=clipped)
                inventory, report = self.report()
                data, manifest = self.build(report, inventory)
                self.assertEqual(manifest["located_count"], 1)
                with fitz.open(stream=data,filetype="pdf") as output:
                    page=output[0]
                    clip=fitz.Rect(expected)+(-6,-6,6,6)
                    pix=page.get_pixmap(clip=clip,alpha=False,annots=True)
                    points=[];samples=bytes(pix.samples)
                    for offset in range(0,len(samples),3):
                        red,green,blue=samples[offset:offset+3]
                        if red>210 and 70<green<205 and blue<105:
                            number=offset//3;points.append((pix.x+number%pix.width,pix.y+number//pix.width))
                    self.assertTrue(points,"No source-region annotation was visible at its expected location")
                    orange=[min(x for x,y in points),min(y for x,y in points),
                            max(x for x,y in points)+1,max(y for x,y in points)+1]
                    self.assertLess(max(abs(a-b) for a,b in zip(orange,expected)),4.1)

    def test_ambiguous_and_graphics_only_evidence_receive_no_invented_mark(self):
        for graphics,repeated in ((False,True),(True,False)):
            with self.subTest(graphics=graphics,repeated=repeated):
                if self.source.exists():self.source.unlink()
                self.make_source(graphics_only=graphics,repeated=repeated)
                inventory, report=self.report()
                data, manifest=self.build(report, inventory)
                self.assertEqual(manifest["located_count"],0)
                self.assertEqual(manifest["unlocated_count"],len(manifest["notes"]))
                with fitz.open(stream=data,filetype="pdf") as output:
                    self.assertEqual(list(output[0].annots() or []),[])
                    text="\n".join(output[i].get_text() for i in range(1,output.page_count))
                    self.assertIn("Unlocated:", text)
                    if repeated:
                        self.assertIn("several possible text matches", text)
                    else:
                        self.assertIn("no reliable text location was recorded", text)
                    for note in manifest["notes"]:
                        self.assertIn(note["note_id"], text)
                        self.assertIsInstance(note["location_reason"], str)

    def test_mismatched_or_missing_source_binding_is_rejected(self):
        self.make_source();inventory,report=self.report()
        for target in ("report","inventory"):
            for digest in (None,"0"*64):
                with self.subTest(target=target,digest=digest):
                    bad_report,bad_inventory=deepcopy(report),deepcopy(inventory)
                    (bad_report if target=="report" else bad_inventory)["source_sha256"]=digest
                    self.assertIsNotNone(build_annotated_pdf)
                    with self.assertRaises(ValueError):build_annotated_pdf(self.source,bad_report,bad_inventory)

    def test_renamed_identical_source_bytes_remain_bound(self):
        self.make_source();inventory,report=self.report()
        renamed=self.root/'renamed.pdf';renamed.write_bytes(self.source.read_bytes())
        self.assertIsNotNone(build_annotated_pdf)
        data,manifest=build_annotated_pdf(renamed,report,inventory)
        self.assertEqual(manifest["located_count"],1)

    def test_replaced_source_file_cannot_reuse_an_old_report(self):
        self.make_source();inventory,report=self.report()
        replacement=fitz.open();page=replacement.new_page();page.insert_text((30,30),'Different invented source')
        current=replacement.tobytes();replacement.close();self.source.write_bytes(current)
        self.assertIsNotNone(build_annotated_pdf)
        with self.assertRaises(ValueError):build_annotated_pdf(self.source,report,inventory)
        self.assertEqual(self.source.read_bytes(),current)

    def test_forged_caller_inventory_and_bbox_cannot_create_a_source_anchor(self):
        self.make_source();inventory,report=self.report()
        fake=[300,300,420,330]
        inventory['spans'][0]['bbox_points']=fake
        report['requirements'][0]['bbox_points']=fake
        report['requirements'][0]['input_evidence']['bbox_points']=fake
        data,manifest=self.build(report,inventory)
        note=next(n for n in manifest['notes'] if n['finding_id']=='CANDIDATE-PLAN-SCALE')
        self.assertIsNone(note['anchor'])
        with fitz.open(stream=data,filetype='pdf') as output:self.assertEqual(list(output[0].annots() or []),[])

    def test_common_unicode_and_explicit_astral_fallback_preserve_note_meaning(self):
        self.make_source();inventory,report=self.report()
        label='Café – ≥ Δ 中文 \U0001F600'
        report['requirements'][0]['review_instruction']=label
        data,manifest=self.build(report,inventory)
        with fitz.open(stream=data,filetype='pdf') as output:
            text='\n'.join(output[i].get_text() for i in range(1,output.page_count))
            self.assertIn('Café – ≥ Δ 中文',text)
            self.assertIn(r'\U0001F600',text)
            self.assertIn(label,next(output[0].annots()).info['content'])

    def test_rtl_text_uses_explicit_fallback_instead_of_reversing_the_printed_words(self):
        self.make_source();inventory,report=self.report()
        label='Review \u05e9\u05dc\u05d5\u05dd \u0645\u0631\u062d\u0628\u0627'
        report['requirements'][0]['review_instruction']=label
        data,manifest=self.build(report,inventory)
        note=next(n for n in manifest['notes'] if n['finding_id']=='CANDIDATE-PLAN-SCALE')
        with fitz.open(stream=data,filetype='pdf') as output:
            text='\n'.join(output[i].get_text() for i in range(1,output.page_count))
            self.assertIn(r'\u05E9\u05DC\u05D5\u05DD',text)
            self.assertIn(r'\u0645\u0631\u062D\u0628\u0627',text)
            self.assertNotIn('\u05e9\u05dc\u05d5\u05dd',text)
            self.assertIn(label,next(output[0].annots()).info['content'])
        self.assertIn(label,note['body'])
        self.assertIn(note['note_id'],manifest['unicode_fallback_note_ids'])

    def test_note_and_print_index_limits_fail_instead_of_truncating(self):
        self.make_source();inventory,report=self.report()
        self.assertIsNotNone(build_annotated_pdf)
        for maximum in (0,True,201):
            with self.subTest(maximum=maximum):
                self.assertIsNotNone(build_annotated_pdf)
                with self.assertRaises(ValueError):build_annotated_pdf(self.source,report,inventory,max_notes=maximum)
        report['requirements'][0]['review_instruction']='X'*4097
        with self.assertRaises(ValueError):build_annotated_pdf(self.source,report,inventory)

    def test_long_notes_paginate_without_dropping_the_end(self):
        self.make_source();inventory,report=self.report()
        body=' '.join('Evidence%03d'%i for i in range(240))+' END_OF_LONG_REVIEW_NOTE'
        report['requirements'][0]['review_instruction']=body
        data,manifest=self.build(report,inventory)
        self.assertGreater(manifest['notes_page_count'],1)
        with fitz.open(stream=data,filetype='pdf') as output:
            text='\n'.join(output[i].get_text() for i in range(1,output.page_count))
            self.assertIn('END_OF_LONG_REVIEW_NOTE',text)
            for index in (0,119,239):self.assertIn('Evidence%03d'%index,text)

    def test_a_continued_note_keeps_its_number_on_each_printed_page(self):
        self.make_source();inventory,report=self.report()
        report['requirements'][0]['review_instruction']='\n'.join('InventedLine%03d'%i for i in range(150))
        data,manifest=self.build(report,inventory)
        note=next(n for n in manifest['notes'] if n['finding_id']=='CANDIDATE-PLAN-SCALE')
        pages=manifest['note_index_pages'][note['note_id']]
        self.assertGreater(len(pages),1)
        with fitz.open(stream=data,filetype='pdf') as output:
            for ordinal in pages:self.assertIn(note['note_id'],output[ordinal-1].get_text())

    def test_index_overflow_is_rejected_before_returning_a_partial_pdf(self):
        self.make_source();inventory,report=self.report()
        seed=report['requirements'][0]
        entries=[]
        for index in range(180):
            entry=deepcopy(seed)
            entry['requirement_id']='INVENTED-%03d'%index
            entry['review_instruction']='Review '+('Long evidence text. '*180)
            entry['publication_title']='Publication '+('Long citation text. '*180)
            entries.append(entry)
        report['requirements']=entries
        self.assertIsNotNone(build_annotated_pdf)
        with self.assertRaisesRegex(ValueError,'page.*limit|limit.*page'):
            build_annotated_pdf(self.source,report,inventory)

    def test_second_source_page_is_distinct_from_publication_and_index_pages(self):
        source=fitz.open();source.new_page(width=600,height=800).insert_text((30,50),'Invented title')
        source.new_page(width=600,height=800).insert_text((100,160),'SCALE 1:5000')
        source.save(self.source);source.close()
        inventory,report=self.report();data,manifest=self.build(report,inventory)
        self.assertEqual(manifest['original_page_count'],2)
        note=next(n for n in manifest['notes'] if n['finding_id']=='CANDIDATE-PLAN-SCALE')
        self.assertEqual(note['anchor']['page'],2)
        self.assertTrue(all(p>2 for p in manifest['note_index_pages'][note['note_id']]))
        with fitz.open(stream=data,filetype='pdf') as output:
            self.assertFalse(list(output[0].annots() or []))
            self.assertEqual(len(list(output[1].annots())),1)
            self.assert_page_only_source_links(output,2,[1])


if __name__ == '__main__':
    unittest.main()
