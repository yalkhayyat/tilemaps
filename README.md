# Overview
This is a scenery generation tool built for Roblox. I began working on this project because of my interest in flight simulation.

There are a few options for massive 1:1 scale scenery on Roblox:
- Stream, decode, and render satellite images and heightmaps natively in Roblox, using either Parts or EditableMesh/EditableImage. This can be done, but is slow and more technically complicated. The main bottleneck is that Roblox doesn't provide a good way to download and decode PNG/JPEG files and access individual pixel values, and Lua isn't the fastest language for the job.
- Request image/heightmap data and render it, without decoding. This requires you to decode and serve map tiles on your own server. It can be faster than the previous option, but EditableMesh and EditableImage now become an issue. First, EditableMeshes are limited to 2048 studs in size, which is not ideal for massively large worlds. Second, there's no fast way to create and update meshes/images in bulk.

This project attempts to solve some of the problems with the above methods. Instead of building out the tiles in real time, the tiles are prebuilt and uploaded to Roblox. The game only has to load the images and meshes from Roblox, which is as fast as we can get. 
The main disadvantage is the tiles *are prebuilt.* This means that we have to choose carefully which tiles to prioritize for the best user experience. We can't generate new tiles on the fly.

# How it works
The tiles are generated based off of a configured QuadTree. High Level-of-Detail (LOD) tiles are generated close to airports and points of interest, with gradually lower LOD tiles farther away. This helps reduce loading times and the overall number of meshes and textures.

After the QuadTree is built, satellite images are requested for each map tile. Each satellite image is then uploaded to Roblox using the Open Cloud API, and we store a JSON table with tiles as keys and Asset IDs as values. For meshes, a heightmap is requested and the mesh is generated accordingly, then uploaded to Roblox.

In the end, you're left with JSON tables mapping tiles to corresponding texture and mesh Asset IDs. The tables can then be used in-game to generate the scenery.
