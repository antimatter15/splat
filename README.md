# splat

This is a WebGL implementation of a real-time renderer for [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/), a recently developed technique for taking a set of pictures and generating a photorealistic navigable 3D scene out of it. As it is essentially an extension of rendering point clouds, rendering scenes generated with this technique can be done very efficiently on ordinary graphics hardware- unlike prior comparable techniques such as NeRFs.

You can [try it out here](https://antimatter15.com/splat/).

https://github.com/antimatter15/splat/assets/30054/6534558e-5ddd-4ca5-a4ba-48d7b7c72af2

## controls

- left and right arrows to rotate left and right
- up and down to move forward and back
- space to jump
- w/s to tilt camera up/down
- a/d to strafe left and right
- q/e to tilt camera left/right
- drag left/right with mouse to rotate left and right
- drag up/down with mouse to move forward and back
- right click and drag to move up/down and left/right
- press 0-9 to switch to one of the pre-loaded camera views

## other features

- press `v` to save the current view coordinates to the url
- open custom `.splat` files by adding a `url` param to a CORS-enabled URL
- drag and drop a `.ply` file which has been processed with the 3d gaussian splatting software onto the page and it will automatically convert the file to the `.splat` format

## examples

note that as long as your `.splat` file is hosted in a CORS-accessible way, you can open it with the `url` field. 

- https://antimatter15.com/splat/?url=plush.splat#[0.95,0.19,-0.23,0,-0.16,0.98,0.12,0,0.24,-0.08,0.97,0,-0.33,-1.52,1.53,1]
- https://antimatter15.com/splat/?url=truck.splat
- https://antimatter15.com/splat/?url=garden.splat
- https://antimatter15.com/splat/?url=treehill.splat
- https://antimatter15.com/splat/?url=stump.splat#[-0.86,-0.23,0.45,0,0.27,0.54,0.8,0,-0.43,0.81,-0.4,0,0.92,-2.02,4.1,1]
- https://antimatter15.com/splat/?url=bicycle.splat


## notes

- written in javascript with webgl 1.0 with no external dependencies, you can just hit view source and read the unminified code. webgl 2.0 doesn't really add any new features that aren't possible with webgl 1.0 with extensions. webgpu is apparently nice but still not very well supported outside of chromium.
- we sorts splats by a combination of size and opacity and supports progressive loading so you can see and interact with the model without having all the splats loaded. 
- does not currently support view dependent shading effects with spherical harmonics, this is primarily done to reduce the file size of the splat format so it can be loaded easily into web browsers. For third-order spherical harmonics we need 48 coefficients which is nearly 200 bytes per splat!
- splat sorting is done asynchronously on the cpu in a webworker. it might be interesting to investigate performing the sort on the gpu with an implementation of bitonic or radix sorting, but it seems plausible to me that it'd be better to let the gpu focus rather than splitting its time between rendering and sorting. 


## acknowledgements

Thanks to Otavio Good for discussions on different approaches for [order independent transparency](https://en.wikipedia.org/wiki/Order-independent_transparency), Mikola Lysenko for [regl](http://regl.party/) and also for helpful advice about webgl and webgpu, Ethan Weber for discussions about how NeRFs work, Gray Crawford for identifying issues with color rendering and camera controls, Anna Brewer for help with implementing animations, and GPT-4 for writing all the WebGL boilerplate. 
