# Examples of MR-Coupler-generated MTCs that are different from developer-written MTCs


### Example 1: correct but different MRs -- over different method pairs

For the `readAndWrite` method, the developer constructed an equivalence MR over `readAndWrite` and `a2q`, while MR-Coupler derives an MR over `readAndWrite(x1) = readAndWrite(x2) (x1 = x2)`. 

* [Developer-written MTC](https://github.com/FasterXML/jackson-core/blob/3.x/src/test/java/tools/jackson/core/unittest/filter/BasicParserFilteringTest.java):
``` java
	@Test
    void multipleMatchFilteringWithPath1() throws Exception
    {
        JsonParser p0 = JSON_F.createParser(ObjectReadContext.empty(), SIMPLE);
        FilteringParserDelegate p = new FilteringParserDelegate(p0,
                new NameMatchFilter("value0", "value2"),
                Inclusion.INCLUDE_ALL_AND_PATH, true /* multipleMatches */ );
        String result = readAndWrite(JSON_F, p);
        assertEquals(a2q("{'ob':{'value0':2,'value2':0.25}}"), result);
        assertEquals(2, p.getMatchCount());

    }	
```

* MR-Coupler-generated MTC:
``` java
	@Test
    public void testMR1_1() throws IOException {
        String input = "{'a':1}";
        JsonFactory f = JSON_FACTORY;
        JsonParser p1 = createParser(MODE_INPUT_STREAM, input);
        String output1 = readAndWrite(f, p1);
        JsonParser p2 = createParser(MODE_INPUT_STREAM, output1);
        String output2 = readAndWrite(f, p2);
        assertEquals(output1, output2);
    }
```


### Example 2: correct but different MRs -- over the same method pair

For the `cosineSimilarity` method, the developer-constructed MR captures self-similarity dominance ($\cos(x, x) \ge \cos(x, y)$ for any vector $y \neq x$), while MR-Coupler derives an equivalence MR ($\cos(x, y) = \cos(x, y)$).

* [Developer-written MTC](https://github.com/diennea/herddb/blob/master/herddb-core/src/test/java/herddb/sql/SimplerPlannerTest.java):
``` java
	@Test
	public void basicVectorTest() {
		List<Float> vector1AsList = Arrays.asList(0.2f, 0.8f);
		float[] vector3raw = new float[]{0f, 1f};
		float[] vector2raw = new float[]{0.1f, 0.9f};
		float v3v3 = CompiledFunction.cosineSimilarity(vector3raw, vector3raw);
		float v3v2 = CompiledFunction.cosineSimilarity(vector3raw, vector2raw);
		assertTrue(v3v2 < v3v3);
	}
```

* MR-Coupler-generated MTC:
``` java
	@Test
    public void testMR1_1() {
        float[] arr1 = new float[]{1.0f, 2.0f, 3.0f};
        float[] arr2 = new float[]{4.0f, 5.0f, 6.0f};
        float result1 = CompiledFunction.cosineSimilarity(arr1, arr2);
        float result2 = CompiledFunction.cosineSimilarity(arr2, arr1);
        assertEquals(result1, result2, 0.0001f);
    }
```


### Example 3: equivalent but differently expressed assertions

Some inconsistencies arise from equivalent but differently expressed assertions, e.g.,  `assertEquals(x,y)` and `assertTrue(x.customizedEquals(y))`.

* [Developer-written MTC](https://github.com/locationtech/proj4j/blob/master/core/src/test/java/org/locationtech/proj4j/datum/NTV2Test.java#L44):
``` java
	@Test
    public void gridShiftNTV2() {
        CoordinateTransform ct = CT.createTransform(cs1, cs2);
        ProjCoordinate expected1 = new ProjCoordinate(299905.060, 4499796.515);
        ProjCoordinate result1 = new ProjCoordinate();
        ct.transform(new ProjCoordinate(300000.0, 4500000.0), result1);

        Assert.assertTrue(expected1.areXOrdinatesEqual(result1, 0.001) &&
                          expected1.areYOrdinatesEqual(result1, 0.001));
	}
```

* MR-Coupler-generated MTC:
``` java
	@Test
    public void testMR1_1() {
		// Metamorphic Relation: Two ProjCoordinate instances with identical x-values but different y-values should be equal within tolerance
        ProjCoordinate coord1 = new ProjCoordinate(10.0, 20.0);
        ProjCoordinate coord2 = new ProjCoordinate(10.0, 20.0001);
        double tolerance = 0.0001;
        
        assertEquals(coord1.x, coord2.x, tolerance);
        assertEquals(coord1.y, coord2.y, tolerance);
    }
```
