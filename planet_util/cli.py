import json
import types
import datetime as dt

from shapely.geometry import shape, mapping, Polygon
from shapely import ops

from planet import api
planet = api.ClientV1()

import click

def build_date_ranges(months):
    today = dt.date.today()
    keydates = [today] + [today-dt.timedelta(days=31*(m+1)) for m in range(months)]
    keydates = ["{}-{}-{}".format(d.year, d.month, d.day) for d in keydates]
    return list(zip(keydates[1:], keydates[:-1]))


def build_request(g, from_date, to_date):
    flt = api.filters.and_filter(
        api.filters.geom_filter(mapping(g.convex_hull)),
        api.filters.date_range("acquired", gt=from_date, lt=to_date),
        api.filters.range_filter("cloud_cover", lt=0.1),
        api.filters.range_filter("view_angle", lt=5.0),
        api.filters.range_filter("sun_elevation", gt=45.0)
    )
    return api.filters.build_search_request(flt, ["PSOrthoTile"])


def build_scene_list(region, date_ranges):
    scenes = []
    coverage = None
    for from_date, to_date in date_ranges:
        print(from_date, to_date)
        results = planet.quick_search(build_request(region, from_date, to_date), sort="acquired asc")
        for item in results.items_iter(limit=1000):
            if coverage is None:
                coverage = shape(item["geometry"])
            else:
                if coverage_area < coverage.union(shape(item["geometry"])).area:
                    coverage = coverage.union(shape(item["geometry"]))
                    coverage_area = coverage.area
            scenes.append(item)
            coverage_area = coverage.area
    print("Coverage:", coverage.intersection(region).area / region.area, "Count:", len(scenes))
    return(scenes)


@click.command(help="Create a planetscope mosaic for a specified geojson geometry")
@click.option("--months", type=int, help="Number of months in the past to use.")
@click.option("--idx", type=int, help="Index of a single geometry to consider inside the GeoJSON file (starting from 0) [optional]", default=None)
@click.option("--test", is_flag=True, default=False)
@click.argument("geom_file", type=click.Path(exists=True))
def mosaic(geom_file, months, idx, test):
    with open(geom_file) as f:
        # TODO: Error handling
        geojson = json.load(f)
        geoms = [shape(rec["geometry"]) for rec in geojson["features"]]

    if idx is None:
        g = ops.cascaded_union(geoms).buffer(0.0)
    else:
        assert idx < len(geoms), "Specified geometry doesn't exist (index out of range)"
        g = geoms[idx]
        region = Polygon([c[:2] for c in g.convex_hull.exterior.coords])

    print(geom_file, idx, months, test)
    scenes = build_scene_list(region, build_date_ranges(months))
    print(len(scenes))


if __name__ == "__main__":
    mosaic()
