# Edge Loop Reducer

A custom, topology modifying add-on to speed up modeling workflows when working with edge loops.

This add-on utilizes the edge loop reduction flow technique described at https://topologyguides.com/loop-reduction
, and visualized as follows:
![Scene](https://github.com/bbartschi14/edge-loop-reducer/blob/main/topologyguide.png)

## Supported Operations
Current # of faces to resulting # of faces:
- `2 to 1` *and* `1 to 2`
- `3 to 1` *and* `1 to 3`
- `4 to 1` *and* `1 to 4`
- `4 to 2`
- `5 to 3`

## Use
The add-on can be accessed from the `View3D > N` panel within Blender.

When in edit mode, select the top-left vertex of the area which you want to modify. Within the add-on panel, set the `Reduction Type` to your desired edge loop operation. From an axis-aligned view, use the `Across Direction` to designate the direction from top-left to top-right. Then set `Down Direction` to the direction from top-left to bottom-left.

When modifying connected topology, uncheck `Dissolve Extra Verts` to maintain connections and create N-gons.
![Scene](https://github.com/bbartschi14/edge-loop-reducer/blob/main/smallgif.gif)
