from boa3_test.tests.test_classes.testengine import TestEngine

nef_path = 'ruler.nef'
folder = '.'
engine = TestEngine(folder)
engine.run(nef_path, 'addPair')
