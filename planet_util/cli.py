import os
import json
import datetime as dt
import asyncio

from shapely.geometry import shape, mapping, Polygon
from shapely import ops

from planet import api
planet = api.ClientV1()

import click

from planet_util.util import coverage, reduce_scenes

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
    for from_date, to_date in date_ranges:
        results = planet.quick_search(build_request(region, from_date, to_date), sort="acquired asc")
        for item in results.items_iter(limit=1000):
            scenes.append(item)
    print("Coverage:",
          ops.cascaded_union([shape(rec["geometry"])
                              for rec in scenes]).intersection(region).area / region.area,
          "Count:",
          len(scenes))
    return(scenes)


@click.group()
def cli():
    click.echo("Planet high level utilities.")


@cli.command(help="Create a planetscope mosaic for a specified geojson geometry")
@click.option("--months", type=int, help="Number of months in the past to use.")
@click.option("--idx", type=int, help="Index of a single geometry to consider inside the GeoJSON file (starting from 0) [optional]", default=None)
@click.option("--output", help="Output GeoJSON file")
@click.argument("geom_file", type=click.Path(exists=True))
def materials(geom_file, months, idx, output):
    with open(geom_file) as f:
        # TODO: Error handling
        geojson = json.load(f)
        geoms = [shape(rec["geometry"]).convex_hull for rec in geojson["features"]]

    if idx is None:
        g = ops.cascaded_union(geoms).buffer(0.0)
    else:
        assert idx < len(geoms), "Specified geometry doesn't exist (index out of range)"
        g = geoms[idx]
    region = Polygon([c[:2] for c in g.convex_hull.exterior.coords])

    scenes = build_scene_list(region, build_date_ranges(months))
    scenes = reduce_scenes(scenes, g)
    click.echo("Reducing to {} scenes while maintaining {}% coverage.".format(len(scenes),
                                                                              100*coverage(scenes, region)))
    scenes_geojson = {
        "type": "FeatureCollection",
        "features": scenes
    }
    with open(output, "w") as f:
        json.dump(scenes_geojson, f)

@cli.command(help="Activate scenes in specified file, if they aren't already")
@click.option("--product", default="visual")
@click.argument("scenes_file", type=click.Path(exists=True))
def activate(scenes_file, product):
    with open(scenes_file) as f:
        scenes = json.load(f)
    click.echo("Activating {} scenes.".format(len(scenes["features"])))
    ready_count = 0
    for idx, scene in enumerate(scenes["features"]):
        assets = planet.get_assets(scene).get()
        assert product in assets, "Desired product doesn't exist for specified scene"
        if assets[product]["status"] == "inactive":
            planet.activate(assets[product])
        elif (assets[product]["status"]) == "active":
            ready_count = ready_count + 1
    click.echo("{}/{} images ready to download".format(ready_count, len(scenes["features"])))

@cli.command(help="Download scenes in specified file, if they haven't been already")
@click.option("--product", default="visual")
@click.option("--path", help="Download images to path", default=os.path.join(os.getcwd(),"planet"), type=click.Path(exists=True))
@click.argument("scenes_file", type=click.Path(exists=True))
def download(scenes_file, product, path):
    with open(scenes_file) as f:
        scenes = json.load(f)

    assets = [planet.get_assets(scene).get()[product] for scene in scenes["features"]]

    for asset in assets:
        click.echo(asset)
        planet.download(asset, api.write_to_file(path)).await()


if __name__ == "__main__":
    cli()
