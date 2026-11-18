// 수정본 Table 2(연도별 유효 장면 수·촬영일·화소당 유효 관측 횟수·북구 평균 LST) 산출용
// 경계: SGIS 집계구 경계(2025년 2분기). 재실행 시 본인 GEE 자산 경로로 바꾸십시오.
var bukgu = ee.FeatureCollection('projects/lateral-plane-500605-i8/assets/bnd_oa_24040_2025_2Q').geometry();

function mask(img) {
  var qa = img.select('QA_PIXEL');
  var m = qa.bitwiseAnd(1 << 3).eq(0).and(qa.bitwiseAnd(1 << 4).eq(0));
  var lst = img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15);
  return lst.updateMask(m).rename('LST').copyProperties(img, ['system:time_start']);
}

[2020, 2025].forEach(function (y) {
  var col = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .filterBounds(bukgu)
    .filterDate(y + '-05-01', y + '-10-01')
    .map(mask)
    // 북구 영역에 유효 화소가 하나라도 있는 장면만
    .map(function (img) {
      var n = img.reduceRegion({reducer: ee.Reducer.count(), geometry: bukgu, scale: 100, maxPixels: 1e9}).get('LST');
      return img.set('valid', n);
    })
    .filter(ee.Filter.gt('valid', 0));

  var dates = col.aggregate_array('system:time_start').map(function (t) {
    return ee.Date(t).format('MM/dd');
  });
  var months = col.aggregate_array('system:time_start').map(function (t) {
    return ee.Date(t).get('month');
  });
  var perPixel = col.count().reduceRegion({reducer: ee.Reducer.mean(), geometry: bukgu, scale: 100, maxPixels: 1e9});
  var meanLst = col.mean().reduceRegion({reducer: ee.Reducer.mean(), geometry: bukgu, scale: 100, maxPixels: 1e9});

  print(y + ' 유효 장면 수', col.size());
  print(y + ' 촬영일', dates);
  print(y + ' 월별 장면 수', months.reduce(ee.Reducer.frequencyHistogram()));
  print(y + ' 화소당 평균 유효 관측 횟수', perPixel);
  print(y + ' 북구 평균 LST(℃)', meanLst);
});
