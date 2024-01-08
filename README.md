# splat

This is a WebGL implementation of a real-time renderer for [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/), a recently developed technique for taking a set of pictures and generating a photorealistic navigable 3D scene out of it. As it is essentially an extension of rendering point clouds, rendering scenes generated with this technique can be done very efficiently on ordinary graphics hardware- unlike prior comparable techniques such as NeRFs.

You can [try it out here](https://antimatter15.com/splat/).



https://github.com/antimatter15/splat/assets/30054/878d5d34-e0a7-4336-85df-111ff22daf4b



## controls

movement (arrow keys)

- left/right arrow keys to strafe side to side
- up/down arrow keys to move forward/back
- `space` to jump

camera angle (wasd)

- `a`/`d` to turn camera left/right
- `w`/`s` to tilt camera up/down
- `q`/`e` to roll camera counterclockwise/clockwise
- `i`/`k` and `j`/`l` to orbit

trackpad
- scroll up/down to orbit down
- scroll left/right to orbit left/right
- pinch to move forward/back
- ctrl key + scroll up/down to move forward/back
- shift + scroll up/down to move up/down
- shift + scroll left/right to strafe side to side

mouse
- click and drag to orbit
- right click (or ctrl/cmd key) and drag up/down to move forward/back
- right click (or ctrl/cmd key) and drag left/right to strafe side to side

touch (mobile)
- one finger to orbit
- two finger pinch to move forward/back
- two finger rotate to rotate camera clockwise/counterclockwise
- two finger pan to move side-to-side and up-down

other
- press 0-9 to switch to one of the pre-loaded camera views
- press '-' or '+'key to cycle loaded cameras
- press `p` to resume default animation
- drag and drop .ply file to convert to .splat
- drag and drop cameras.json to load cameras

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
- https://antimatter15.com/splat/?url=https://media.reshot.ai/models/nike_next/model.splat#[0.95,0.16,-0.26,0,-0.16,0.99,0.01,0,0.26,0.03,0.97,0,0.01,-1.96,2.82,1]

## notes

- written in javascript with webgl 1.0 with no external dependencies, you can just hit view source and read the unminified code. webgl 2.0 doesn't really add any new features that aren't possible with webgl 1.0 with extensions. webgpu is apparently nice but still not very well supported outside of chromium.
- we sorts splats by a combination of size and opacity and supports progressive loading so you can see and interact with the model without having all the splats loaded. 
- does not currently support view dependent shading effects with spherical harmonics, this is primarily done to reduce the file size of the splat format so it can be loaded easily into web browsers. For third-order spherical harmonics we need 48 coefficients which is nearly 200 bytes per splat!
- splat sorting is done asynchronously on the cpu in a webworker. it might be interesting to investigate performing the sort on the gpu with an implementation of bitonic or radix sorting, but it seems plausible to me that it'd be better to let the gpu focus rather than splitting its time between rendering and sorting.
- earlier experiments used [stochastic transparency](https://research.nvidia.com/publication/2011-08_stochastic-transparency) which looked grainy, and [weighted blended order independent transparency](https://learnopengl.com/Guest-Articles/2020/OIT/Weighted-Blended) which didn't seem to work.


## words

gaussian splats are very efficient to render because they work in a way which is very similar to point clouds— in fact they use the same file format (`.ply`) and open them up with the same tools (though to see colors in meshlab, you should convert the spherical harmonic zeroth order terms into rgb colors first). you can think of them as essentially generalizing individual points into translucent 3D blobs (the eponymous splats). 

that said, even though the inference process is very similar to a traditional 3d rendering, the reference implementation doesn't leverage any of that because for training it needs the entire render pipeline to be differentiable (i.e. you need to be able to run the rendering process "backwards" to figure out how to wiggle the location, size and color of each blob to make a particular camera's view incrementally closer to that of a reference photograph). whether or not this gradient based optimization counts as neural is i guess a somewhat debated question online.

since this implementation is just a viewer we don't need to do any differentiable rendering. our general approach is to take each splat and feed it into a vertex shader. we take the xyz position of the splat and project it to the screen coordinates with a projection matrix, and we take the scale and quaternion rotation parameters of the splat and figure out the projected eigenvectors so we can draw a bounding quadrilateral. these quadrilaterals are then individually shaded with a fragment shader. 

the fragment shader is a program which essentially runs for each pixel on each fragment (i.e. quadrilateral that was generated by the vertex shader) and outputs a color. It takes its position, calculates the distance from the center of the splat and uses it to determine the opacity channel of the splat's color. right now this implementation only stores 3 (red, blue, green) channels of color for a splat, but the full implementation uses essentially 48 channels to encode arbitrary view-dependent lighting. 

the most annoying problem comes with how these fragments come together and create an actual image. it turns out that rendering translucent objects in general is a somewhat unsolved problem in computer graphics which ultimately stems from the fact that compositing translucent things is not commutative, i.e. a stack of translucent objects looks different based on the order in which they are drawn. 

one easy solution is called speculative transparency, where basically you pretend that you actually have no translucency at all- objects are just different levels of randomized swiss cheese. the graphics card keeps track of a z-buffer and discards all the pixels which are not the top-most, and we generate a random number at each pixel and then discard it if it 90% of the time if it is 90% transparent. this works but it gives everything a noisy, dithered look.

another easy approach is to use the painter's algorithm, which basically involves pre-sorting all your objects before rendering them. doing this on the CPU can be rather expensive, with the ~1M splats on the demo page, it takes about 150ms to sort through them all on my computer. 

the approach that the reference implementation, and most other implementations of gaussian splatting take is to do the sorting on the GPU. one common algorithm for doing sorts on the gpu is called the [bitonic sort](https://en.wikipedia.org/wiki/Bitonic_sorter) as it is very parallelizable. a normal cpu comparison sorting algorithm like quicksort/mergesort can run in O(n log n) time, the bitonic sort is a bit slower at O(n log^2 n), but the n factor can be done in parallel, so the overall latency is O(log^2 n) which is faster than than O(n log n). the reference implementation uses a radix sort based on [onesweep](https://arxiv.org/abs/2206.01784), which can happen in O(n) time because you can leverage the fact that you're sorting numbers to get more information at each cycle than a single comparison. 

chrome has recently shipped webgpu, which is a new very clean api that apparently makes it possible to write things like compute shaders similar to CUDA that work in the browser. however, webgpu is not yet supported by firefox and safari. this means that if we want to build something that is broadly usable, we have to stick with the older webgl (and maybe even webgl 1.0, since there are reports that webgl 2.0 is buggy or slow on safari with the new M1 chips). It's still probably possible to implement a bitonic sort on top of webgl, but it would take about 200 iterations to sort 1M numbers, so it might still be too slow. 

another approach to rendering translucent objects is called depth peeling, where you enable the z-buffer and only render the translucent objects that are on the top, and then feed that z-buffer back into the render process to "peel" off the top and render only the layer beneath, before stacking those translucent layers together to a final image. I didn't manage to get this to work, but it's likely that it would be slow anyway.

another interesting approach is something called [weighted blended order independent transparency](https://learnopengl.com/Guest-Articles/2020/OIT/Weighted-Blended) which adds an additional number saved to a different render buffer which is used as a weight for an approximation of translucency which is commutative. it didn't work in my experiments, which is somewhat expected in situations where you have certain splats with high opacity on top of each other. 

the final approach that i settled on is to run the sorting process on the CPU in a webworker, which happens a bit more slowly (at roughly 4fps whereas the main render is at 60fps), but that's fine because most of the time when you are moving around the z order doesn't actually change very fast (this results in momentary artifacts when jumping directly between different camera orientations on opposite sides). 


## acknowledgements

Thanks to Otavio Good for discussions on different approaches for [order independent transparency](https://en.wikipedia.org/wiki/Order-independent_transparency), Mikola Lysenko for [regl](http://regl.party/) and also for helpful advice about webgl and webgpu, Ethan Weber for discussions about how NeRFs work and letting me know that sorting is hard, Gray Crawford for identifying issues with color rendering and camera controls, Anna Brewer for help with implementing animations, and GPT-4 for writing all the WebGL boilerplate. 
