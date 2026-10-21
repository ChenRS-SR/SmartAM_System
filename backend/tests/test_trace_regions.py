"""外围机械结构不应进入因果分区；无归因证据也不能掩盖已识别异常。"""
import unittest
import numpy as np
from analysis_engine.results import conclusion
from analysis_engine.service import AnalysisPackage
from forming_monitor.engine import preprocess as P


class RegionTests(unittest.TestCase):
    def test_edge_blade_body_excluded_but_inner_multiple_parts_preserved(self):
        candidate = np.zeros((600, 800), np.uint8)
        candidate[:, 20:26] = 1
        candidate[:, 120:126] = 1
        candidate[180:360, 220:380] = 1
        candidate[380:550, 600:770] = 1  # 靠边的真实零件不能按居中假设删除。
        excluded = P._hardware_exclusion(candidate)
        self.assertTrue(excluded[:, :126].all())
        self.assertFalse(excluded[180:360, 220:380].any())
        self.assertFalse(excluded[380:550, 600:770].any())

    def test_flat_input_has_empty_regions_and_padding_is_not_powder(self):
        frame = np.full((600, 900, 3), 100, np.uint8)
        with np.errstate(all='raise'):
            part, band, valid = P.part_regions(frame, frame, [0, 0, 900, 600], 12)
        self.assertFalse(part.any())
        self.assertFalse(band.any())
        self.assertFalse(valid[0].any())
        self.assertTrue(valid[112].all())

    def test_b44_real_parts_remain_and_hardware_is_not_reassigned_to_powder(self):
        p = AnalysisPackage('b44-20250321-09-20')
        sample = p.inputs(15)
        self.assertFalse(sample['part'][:, :4].any())
        self.assertFalse(sample['band'][:, :4].any())
        self.assertTrue(sample['part'][:, 40:112].any())
        self.assertTrue(sample['part'][:, 112:210].any())
        for item in p.meta['layers']:
            s = p.inputs(item['layer'])
            self.assertFalse((s['part'] & ~s['band']).any())
            self.assertFalse((s['band'] & ~s['valid']).any())

    def test_shapley_coalitions_keep_hardware_fixed(self):
        from analysis_engine.runtime import Runtime
        runtime = Runtime.__new__(Runtime)
        runtime.meta = {'architecture': 'vis_torque'}
        calls = []
        def forward(images, torque):
            calls.append(images.copy())
            values = images.sum(axis=(1,2,3)).astype(float)
            z = np.stack([values, values], axis=1)
            return z, np.full_like(z, .2), {'vis': np.full_like(z, .2)}
        runtime.forward = forward
        rgb = np.full((4, 4, 3), 10, np.uint8)
        valid = np.ones((4,4), bool); valid[:,0] = False
        band = np.zeros_like(valid); band[:,1] = True
        result = runtime.infer({'rgb':rgb, 'band':band, 'valid':valid}, {'rgb':np.zeros_like(rgb)})
        coalitions = calls[1]
        self.assertTrue((coalitions[:,:,0,:] == 10).all())
        self.assertTrue((coalitions[0,:,1:,:] == 0).all())
        np.testing.assert_array_equal(coalitions[3],rgb)
        self.assertAlmostEqual(result['dev_part']+result['dev_powder'], 360)


class ConclusionTests(unittest.TestCase):
    def test_probabilities_and_contributions_have_distinct_pending_states(self):
        for proc_on in (False,True):
            for dev_on in (False,True):
                factors = {'proc':{'present':proc_on}, 'dev':{'present':dev_on}}
                for proc_p in (.1,.5,.9):
                    for dev_p in (.1,.5,.9):
                        result = conclusion({'p_proc':proc_p,'p_dev':dev_p},factors)
                        if max(proc_p,dev_p)>=.5 or proc_on or dev_on:
                            self.assertNotEqual(result,'未见异常')
        factors = {'proc':{'present':False},'dev':{'present':False}}
        self.assertEqual(conclusion({'p_proc':.01,'p_dev':.65},factors),'已识别异常，归因待确认')
        factors['dev']['present'] = True
        self.assertEqual(conclusion({'p_proc':.01,'p_dev':.1},factors),'贡献超限，待复核')
        self.assertEqual(conclusion({'p_proc':.01,'p_dev':.65},factors),'由设备因素诱发')

    def test_b44_anomalous_layers_are_not_reported_as_normal(self):
        p = AnalysisPackage('b44-20250321-09-20')
        for layer in (23,25,26):
            result = p.archived[str(layer)]
            self.assertGreater(result['row']['p_dev'],.5)
            self.assertEqual(result['trace']['conclusion'],'已识别异常，归因待确认')
            self.assertEqual(result['trace']['actions'],['复核异常层与归因证据'])

if __name__ == '__main__': unittest.main()
