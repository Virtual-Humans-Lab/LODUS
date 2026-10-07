import csv
import tempfile
import unittest
from pathlib import Path
import numpy as np
import networkx as nx
from pipeline.od import estimate_od
from pipeline.ingest import population_frames, priors, extensions
from pipeline.routing import Router
from pipeline.build import canonical, environment_index


class GeographyTests(unittest.TestCase):
    def test_legacy_neighborhood_aliases(self):
        for legacy, official in [('Centro', 'Centro Histórico'),
                                 ('Coronel Aparício Borges', 'Cel. Aparicio Borges'),
                                 ('Jardim Dona Leopoldina', 'Jardim Leopoldina'),
                                 ('Jardim Itu', 'Jardim Itú'),
                                 ('MontSerrat', "Mont'Serrat"),
                                 ('Passo DAreia', 'Passo Da Areia'),
                                 ('Vila São José', 'São José')]:
            with self.subTest(legacy=legacy):
                self.assertEqual(canonical(legacy), canonical(official))
        self.assertNotEqual(canonical('Centro desconhecido'), canonical('Centro Histórico'))

    def test_environment_alias_preserves_simulation_node_ids(self):
        environments = [{'name': 'Centro Histórico', 'lng_lat': [-51.22, -30.03],
                         'points_of_interest': [{'name': 'work', 'unique_name': 'office',
                                                 'lng_lat': [-51.23, -30.04]}]}]
        env, pois = environment_index(environments, ['Centro', 'Unknown'])
        self.assertEqual(env['Centro']['lng_lat'], [-51.22, -30.03])
        self.assertEqual(pois['Centro//work'], [-51.23, -30.04])
        self.assertEqual(pois['Centro//office'], pois['Centro//work'])
        self.assertNotIn('Unknown', env)
        self.assertNotIn('Centro Histórico//work', pois)
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            environment_index(environments + [dict(environments[0], name='Centro')], ['Centro'])


class EstimatorTests(unittest.TestCase):
    def test_marginals_and_cost_preference(self):
        costs=np.array([[0,1,1,50],[1,0,50,1],[1,50,0,1],[50,1,1,0]])
        t,r=estimate_od([-10,-20,10,20],costs,beta=.1)
        np.testing.assert_allclose(t.sum(1),[10,20,0,0],atol=3e-6)
        np.testing.assert_allclose(t.sum(0),[0,0,10,20],atol=3e-6)
        self.assertGreater(t[0,2],t[0,3]);self.assertLess(r['max_marginal_error'],3e-6)

    def test_residual_normalization_is_auditable(self):
        t,r=estimate_od([-250,200],[[0,2],[2,0]])
        self.assertAlmostEqual(t[0,1],250);self.assertEqual(r['residual'],-50);self.assertEqual(r['attraction_scale'],1.25)
        with self.assertRaisesRegex(ValueError,'strict'):estimate_od([-250,200],[[0,2],[2,0]],balance='strict')

    def test_zero_and_one_sided(self):
        t,_=estimate_od([0,0],[[0,1],[1,0]])
        self.assertEqual(t.sum(),0)
        for d in ([10,0],[-10,0]):
            with self.assertRaisesRegex(ValueError,'source/sink'):estimate_od(d,[[0,1],[1,0]])

    def test_structural_zeros_and_infeasible_support(self):
        costs=np.full((4,4),np.inf);costs[0,2]=1;costs[1,3]=1
        t,_=estimate_od([-10,-20,10,20],costs)
        self.assertEqual(t[0,3],0)
        with self.assertRaisesRegex(ValueError,'converge'):estimate_od([-20,-10,10,20],costs,max_iterations=20)
        with self.assertRaisesRegex(ValueError,'Unreachable'):estimate_od([-1,1],[[0,np.inf],[1,0]])

    def test_long_costs_do_not_underflow(self):
        t,_=estimate_od([-1,1],[[0,1e7],[1e7,0]],beta=1)
        self.assertAlmostEqual(t[0,1],1)

    def test_invalid_inputs(self):
        for d,c in [([np.nan,0],np.zeros((2,2))),([-1,1],[[0,-1],[1,0]]),([-1,1],[[0,np.nan],[1,0]])]:
            with self.assertRaises(ValueError):estimate_od(d,c)
        with self.assertRaises(ValueError):estimate_od([-1,1],[[0,1],[1,0]],prior=[[1,0],[1,1]])

    def test_functional_prior_keeps_marginals(self):
        c=np.ones((4,4));p=np.ones((4,4));p[0,2]=10
        t,_=estimate_od([-10,-10,10,10],c,prior=p)
        self.assertGreater(t[0,2],t[0,3]);np.testing.assert_allclose(t.sum(1),[10,10,0,0],atol=2e-6)


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def write_population(self, hours=24, duplicate=False, corrupt=False, delimiter=';'):
        path=self.root/'regions.csv'
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f,delimiter=delimiter)
            w.writerow(['Frame','Hour','Day','Region','Total','Locals','Outsiders','dTotals','dLocals','dOutsiders'])
            for hour in range(hours):w.writerow([hour,hour,0,'Cidade Baixa',100+hour,100+hour,0,99 if corrupt and hour==5 else 1,99 if corrupt and hour==5 else 1,0])
            if duplicate:w.writerow([0,0,0,'Cidade Baixa',100,100,0,1,1,0])
        return path
    def test_all_frames_and_incoming_delta(self):
        for delimiter in [';',',']:
            result=population_frames(self.write_population(delimiter=delimiter),'Region')
            self.assertEqual(len(result),24);self.assertEqual(result[1]['Cidade Baixa']['Total'],101)
    def test_reject_missing_duplicates_and_bad_deltas(self):
        for kwargs in [{'hours':23},{'duplicate':True},{'corrupt':True}]:
            with self.assertRaises(ValueError):population_frames(self.write_population(**kwargs),'Region')
    def test_priors_and_empty_extensions(self):
        path=self.root/'output.txt';path.write_text('Children:275\nYoungs:526\nAdults:2806\nElders:1226\nWorker:2646\nStudent:1042\nOther:1145\nmove_population',encoding='utf8')
        self.assertEqual(sum(priors(path)['age']),4833)
        self.assertEqual(priors(path)['plugins'],['move_population'])
        self.assertEqual(extensions(self.root)['nodes_sir'],[])


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.graph=nx.MultiDiGraph()
        for i,p in enumerate([(-51.2,-30),(-51.199,-30),(-51.199,-30.001)]):self.graph.add_node(i,x=p[0],y=p[1])
        self.graph.add_edge(0,1,travel_time=10,length=100)
        self.graph.add_edge(1,2,travel_time=20,length=100)
        self.router=Router(self.graph,{'a':[-51.2,-30],'b':[-51.199,-30.001]})
    def test_route_follows_bend_and_speeds(self):
        r=self.router.route('a','b')[0]
        self.assertEqual(len(r['path']),3)
        self.assertEqual(r['seconds'],[0,10,30]);self.assertEqual(r['duration'],30)
        self.assertEqual(r['path'][1],[-51.199,-30])
    def test_one_way_cannot_be_reversed(self):
        self.assertEqual(self.router.route('b','a'),[])
    def test_no_long_snap_or_fabricated_same_node_path(self):
        with self.assertRaises(ValueError):Router(self.graph,{'far':[-50,-29]},max_snap_m=100)
        self.assertEqual(self.router.route('a','a'),[])


if __name__=='__main__':unittest.main()
