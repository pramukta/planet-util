from shapely import ops
from shapely.geometry import shape

from tqdm import trange

def coverage(scenes, region):
    g = ops.cascaded_union([shape(scene["geometry"]) for scene in scenes])
    return g.intersection(region).area / region.area


def reduce_scenes(scenes, region):
    recs = sorted([(shape(scene["geometry"]).intersection(region).area, scene) for scene in scenes],
                  key=lambda x: x[0])
    removal_list = []
    ref_coverage = coverage(scenes, region)
    for idx in trange(len(scenes)):
        s = [rec[-1] for i, rec in enumerate(recs) if i != idx and i not in removal_list]
        if coverage(s, region) == ref_coverage:
            removal_list.append(idx)
    return [rec[-1] for i, rec in enumerate(recs) if i not in removal_list]
