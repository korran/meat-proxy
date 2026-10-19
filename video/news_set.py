"""SINN (Super-Intelligence News Network): the Anchor's news studio, built from toy bricks at
the cast's scale. She stands in front of a curved video wall and the lit SINN sign ("SI" in
amber and bigger, "NN" a white ribbon). The broadcast graphics (the news
scroller at the bottom, where the lyrics go, and the square graphics box on the right) are a
separate 2D overlay laid over the camera image: see news_overlay.py.

  blender -b --factory-startup --python video/news_set.py -- --out video/build/news_stills \\
      [--preview] [--res 1080] [--only anchor,wide]

Layout, in studs (one stud = 0.136 units, see bricks.py); the Anchor stands at the origin facing -y
(toward the camera). The video wall curves round behind her (radius about 13 studs); the floor
runs y -30..16.
"""
import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lab as SL  # noqa: E402
from bricks import BR, P, PL, Kit  # noqa: E402
from office_set import camera, glass_material, image_material, picture, place_figure  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "build", "news")

AMBER, NN_WHITE = "#ffb21c", "#f2f6ff"            # the logo: SI amber, NN white
NAVY, NAVY2, STEEL = "#0e1a3a", "#1b2c5c", "#8a93a6"
FLOOR, FLOOR2 = "#141a2c", "#1d2540"
GLOW = "#3fd0ff"
ANCHOR_SPOT = (0.0, 0.0)                          # where she stands (studs)
WALL_R, WALL_A = 13.0, 1.25                       # video wall radius (studs) and half-angle (rad)


def textures():
    """The video wall's picture: deep space (stars, a faint nebula, a data grid) over the
    glowing limb of the Earth at night (the Dyson sphere in front of it is 3D, see globes())."""
    os.makedirs(TEX, exist_ok=True)
    path = os.path.join(TEX, "wall.png")
    if os.path.exists(path):
        return
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    w, h = 4096, 1830           # the wall's own proportions (about 4.4 x 1.96 units)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):     # deep blue gradient
        u = y / h
        c = (int(3 + 8 * u), int(5 + 14 * u), int(16 + 34 * u))
        for x in range(w):
            px[x, y] = c
    rng = random.Random(3)
    # deep space: a faint purple-blue nebula, stars
    neb = Image.new("RGB", (w // 8, h // 8))
    npx = neb.load()
    for y in range(h // 8):
        for x in range(w // 8):
            v = (math.sin(x * 0.045) * math.cos(y * 0.06 + x * 0.01) + math.sin(x * 0.013 + y * 0.03)) * 0.5
            v = max(0.0, v)
            npx[x, y] = (int(40 * v), int(20 * v), int(70 * v))
    neb = neb.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30))
    im = ImageChops.add(im, neb)
    dr = ImageDraw.Draw(im)
    for _ in range(2600):
        x, y = rng.randrange(w), rng.randrange(int(h * 0.66))
        b_ = rng.random() ** 3
        c = int(120 + 135 * b_)
        r_ = 1 if b_ < 0.8 else 2
        dr.ellipse([x - r_, y - r_, x + r_, y + r_], fill=(c, c, min(255, c + 20)))
    # a faint data grid over it
    for x in range(0, w, 96):
        dr.line([(x, 0), (x, h)], fill=(26, 52, 110), width=1)
    for y in range(0, h, 96):
        dr.line([(0, y), (w, y)], fill=(26, 52, 110), width=1)
    # the Earth's limb along the bottom: a dark planet under a glowing blue atmosphere
    R = w * 1.6
    cx, cy = w / 2, h * 0.66 + R          # (the horizon is behind her shoulders in the anchor shot)
    for k, col in enumerate(((40, 110, 255), (90, 170, 255), (180, 220, 255))):   # atmosphere, inner brightest
        e = 18 - 6 * k
        dr.ellipse([cx - R - e, cy - R - e, cx + R + e, cy + R + e], outline=col, width=8)
    dr.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(6, 12, 30))
    for _ in range(500):          # city lights on the night side
        a = rng.uniform(-0.28, 0.28)
        rr = R - rng.uniform(4, 400)
        x, y = cx + rr * math.sin(a), cy - rr * math.cos(a)
        if 0 <= x < w and y < h:
            dr.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=(255, 196, 110))
    glow = im.filter(ImageFilter.GaussianBlur(10))
    im = ImageChops.add(im, ImageChops.multiply(glow, Image.new("RGB", (w, h), (110, 110, 110))))
    im.save(path)


# The 'NN': one heavy rounded stroke per N, the two tied together by a stroke running under
# both (unit height; the stroke's centreline, x from 0 to NN_W).
NN_PATHS = [[(0.0, -0.3), (0.0, 1.0), (0.72, 0.0), (0.72, 1.0)],
            [(1.17, 0.0), (1.17, 1.0), (1.89, 0.0), (1.89, 1.0)],
            [(0.0, -0.3), (1.89, -0.3)]]
NN_W, NN_STROKE = 1.89, 0.24
SI_CAP = 1.6          # the height of "SI" (its caps) relative to the NN


def logo(col, x, y, z, h, rot_z=0.0, depth=0.04, emit=3.0, name="logo", dim=1.0):
    """The SINN logo in lit 3D: 'SI' in amber letters a third bigger, 'NN' a white rounded
    ribbon, on one baseline; (x, y, z) is the bottom-left of 'SI', h the height of 'NN'. dim
    darkens the colours (for a subtle sign in the background). Returns the root."""
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    root.location = (x, y, z)
    root.rotation_euler = (math.pi / 2, 0, rot_z)     # letters stand up, facing -y
    font = bpy.data.fonts.load("/usr/share/fonts/opentype/inter/Inter-Black.otf", check_existing=True)
    def mat(color):
        m = bpy.data.materials.new(f"{name}_{color}")
        m.use_nodes = True
        bs = m.node_tree.nodes["Principled BSDF"]
        rgb = (*[c * dim for c in SL.srgb(color)], 1)
        bs.inputs["Base Color"].default_value = rgb
        bs.inputs["Emission Color"].default_value = rgb
        bs.inputs["Emission Strength"].default_value = emit
        bs.inputs["Roughness"].default_value = 0.3
        m.diffuse_color = rgb
        return m

    cu = bpy.data.curves.new(f"{name}_SI", "FONT")
    cu.body, cu.font, cu.size = "SI", font, h * SI_CAP / 0.727
    cu.extrude, cu.bevel_depth = depth / 2, depth * 0.15
    si = bpy.data.objects.new(f"{name}_SI", cu)
    col.objects.link(si)
    si.parent = root
    si.location = (0, -NN_STROKE * h / 2, depth / 2)
    cu.materials.append(mat(AMBER))
    bpy.context.view_layer.update()
    # NN: flat strokes (a box per segment, a disc at every joint and end), extruded to the depth
    x0 = si.dimensions.x + h * 0.14 + NN_STROKE * h / 2
    r = NN_STROKE * h / 2
    V, F = [], []

    def prism(outline):
        n, k = len(outline), len(V)
        V.extend((x, y, 0.0) for x, y in outline)
        V.extend((x, y, depth) for x, y in outline)
        F.append(tuple(range(k + n - 1, k - 1, -1)))
        F.append(tuple(range(k + n, k + 2 * n)))
        F.extend((k + i, k + (i + 1) % n, k + n + (i + 1) % n, k + n + i) for i in range(n))

    for path in NN_PATHS:
        pts = [(x0 + px * h, py * h) for px, py in path]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            ln = math.hypot(bx - ax, by - ay)
            nx, ny = -(by - ay) / ln * r, (bx - ax) / ln * r
            prism([(ax + nx, ay + ny), (ax - nx, ay - ny), (bx - nx, by - ny), (bx + nx, by + ny)])
        for px, py in pts:
            prism([(px + r * math.cos(math.tau * i / 20), py + r * math.sin(math.tau * i / 20)) for i in range(20)])
    me = bpy.data.meshes.new(f"{name}_NN")
    me.from_pydata(V, [], F)
    me.materials.append(mat(NN_WHITE))
    nn = bpy.data.objects.new(f"{name}_NN", me)
    col.objects.link(nn)
    nn.parent = root
    return root


def build_studio(B, col):
    K = Kit(B)
    # floor: big dark tiles, a lighter ring around her
    K.box(-34 * P, -34 * P, -0.03, 34 * P, 20 * P, 0.0, FLOOR)
    for x in range(-30, 30, 4):
        for y in range(-30, 16, 4):
            r = math.hypot(x + 2, y + 2)
            K.tile(x, y, -1, 4, 4, FLOOR2 if 9 < r < 13 else FLOOR, kind="glossy")
    # video wall: flat panels round an arc behind her, on a brick plinth, with a steel frame
    # columns with light strips at the ends of the wall, a truss overhead
    for s in (-1, 1):
        a = s * (WALL_A + 0.12)
        cx, cy = WALL_R * math.sin(a), WALL_R * math.cos(a)
        for z in range(0, 54, 3):
            K.brick(cx - 1, cy - 1, z, 2, 2, NAVY2, studs=False)
        K.box((cx - 0.15) * P, (cy - 1.06) * P, 2 * PL, (cx + 0.15) * P, (cy - 1.0) * P, 52 * PL, GLOW, kind="glow")
    K.box(-16 * P, 8 * P, 56 * PL, 16 * P, 9 * P, 57.5 * PL, STEEL, kind="chrome")
    K.box(-16 * P, 5 * P, 56 * PL, 16 * P, 6 * P, 57.5 * PL, STEEL, kind="chrome")
    for x in range(-14, 16, 4):
        K.box((x - 0.1) * P, 5 * P, 56.2 * PL, (x + 0.1) * P, 9 * P, 57.3 * PL, STEEL, kind="chrome")
        K.cyl(x * P, 4.6 * P, 52 * PL, 56 * PL, 0.04, "#2a2d33", sides=12)
    room = K.build("studio")
    # the wall panels
    wall = image_material("newswall", os.path.join(TEX, "wall.png"), 1.6)
    n = 7
    pw = 2 * WALL_R * math.sin(WALL_A / n) * P
    for k in range(n):
        a = -WALL_A + (k + 0.5) * 2 * WALL_A / n
        K2 = Kit(B)
        K2.box(-pw / 2 - 0.02, 0.0, 0.0, pw / 2 + 0.02, 0.06, 0.12, "#0b0f1c")            # plinth
        K2.box(-pw / 2 - 0.02, 0.0, 0.12, pw / 2 + 0.02, 0.04, 2.1, "#0b0f1c")             # frame
        fr = K2.build(f"wallpanel{k}")
        fr.location = (WALL_R * P * math.sin(a), WALL_R * P * math.cos(a), 0)
        fr.rotation_euler.z = -a
        sc = picture(col, f"wallimg{k}", wall, (0, -0.002, 1.11), (pw - 0.01, 1.96), "-y")
        uv = sc.data.uv_layers[0].data
        u0, u1 = k / n, (k + 1) / n
        for i, (u, v) in enumerate(((u0, 0), (u1, 0), (u1, 1), (u0, 1))):
            uv[i].uv = (u, v)
        sc.parent = fr
    # the SINN sign: big lit letters on the wall over her right shoulder (screen left; the graphics
    # box covers the right of the frame), set along the wall's curve
    a = -0.6
    r = WALL_R * P - 0.1
    logo(col, r * math.sin(a), r * math.cos(a), 0.86, 0.2, rot_z=-a * 0.75, emit=0.3, dim=0.22, name="sign")
    return room


def lighting(sc, spot):
    """Studio lights: a soft key from front left, fill from front right, a warm rim from behind,
    spots from the truss onto the wall; dark room."""
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.01, 0.012, 0.025, 1)
    bg.inputs[1].default_value = 1.0
    ox, oy, oz = spot
    for name, loc, energy, size, color, target in (
            ("studio_key", (-1.2, -2.2, 1.7), 160, 1.4, (1.0, 0.95, 0.9), (0, 0, 0.55)),
            ("studio_fill", (1.6, -2.0, 1.1), 60, 1.8, (0.8, 0.88, 1.0), (0, 0, 0.5)),
            ("studio_rim", (0.6, 1.2, 1.6), 90, 1.0, (1.0, 0.85, 0.65), (0, 0, 0.6)),
            ("studio_wall", (0.0, -0.3, 2.6), 120, 3.0, (0.6, 0.75, 1.0), (0, 1.6, 0.6))):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        lo = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(lo)
        lo.location = (ox + loc[0], oy + loc[1], oz + loc[2])
        SL.aim(lo, (ox + target[0], oy + target[1], oz + target[2]))


# the floating Dyson spheres: (start position, end position over the clip, radius, spin turns per minute)
GLOBES = [((0.12, 1.2, 1.0), (0.32, 1.2, 1.06), 0.48, 1.5)]   # behind her, peeking out right of her head


def _emission(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*SL.srgb(color), 1)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb(color), 1)
    return m


def panel_material(k):
    """Dyson panels: each face has a 'build' value (when it launches, 0..1). Panels are tinted
    glass that fades in during the flight, glowing gold while flying and just after landing,
    then settling to solar-panel blue. (The fly-in modifier hides panels still waiting.)"""
    m = bpy.data.materials.new(f"dyson{k}")
    m.use_nodes = True
    m.surface_render_method = "DITHERED"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "build"
    prog = nt.nodes.new("ShaderNodeValue")
    prog.name = "progress"
    prog.outputs[0].default_value = 0.5
    age = nt.nodes.new("ShaderNodeMath")          # how long ago it was placed (in progress units)
    age.operation = "SUBTRACT"
    nt.links.new(prog.outputs[0], age.inputs[0])
    nt.links.new(attr.outputs["Fac"], age.inputs[1])
    fresh = nt.nodes.new("ShaderNodeMapRange")    # 1 just placed .. 0 after a while
    fresh.inputs["From Min"].default_value, fresh.inputs["From Max"].default_value = FLY, FLY + 0.05
    fresh.inputs["To Min"].default_value, fresh.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(age.outputs[0], fresh.inputs["Value"])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["A"].default_value = (*SL.srgb("#2f6fd6"), 1)
    col.inputs["B"].default_value = (*SL.srgb("#ffc24a"), 1)
    nt.links.new(fresh.outputs["Result"], col.inputs["Factor"])
    strength = nt.nodes.new("ShaderNodeMapRange")
    strength.inputs["To Min"].default_value, strength.inputs["To Max"].default_value = 1.7, 2.8
    nt.links.new(fresh.outputs["Result"], strength.inputs["Value"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(col.outputs["Result"], em.inputs["Color"])
    nt.links.new(strength.outputs["Result"], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    # semi-transparent glass panels that fade in slowly while flying in (age runs from -FLY at
    # launch to 0 on landing)
    fade = nt.nodes.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value, fade.inputs["From Max"].default_value = -FLY, FLY * 0.5
    fade.inputs["To Min"].default_value, fade.inputs["To Max"].default_value = 0.0, PANEL_OPACITY
    nt.links.new(age.outputs[0], fade.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fade.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*SL.srgb("#2f6fd6"), 1)
    return m


def dyson_shell(name, r, seed, gap=0.82):
    """A sphere of separate panels (an icosphere's faces, each shrunk toward its centre so the
    seams show), with a per-face 'build' order: from the bottom up, with some randomness."""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
    rng = random.Random(seed)
    V, F, order = [], [], []
    for f in bm.faces:
        c = f.calc_center_median()
        k = len(V)
        for v in f.verts:
            V.append(tuple(c + (v.co - c) * gap))
        F.append(tuple(range(k, k + len(f.verts))))
        order.append(0.7 * (c.z / r + 1) / 2 + 0.3 * rng.random())
    bm.free()
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], F)
    at = me.attributes.new("build", "FLOAT", "FACE")
    at.data.foreach_set("value", order)
    return me


def fly_in_nodes(name):
    """Geometry nodes for the panels: 'Progress' (0..1) against each panel's 'build' value. A
    panel waits out of sight until its turn, then flies in from far outside (radially, easing to
    a stop) over FLY, and stays put."""
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Progress", in_out="INPUT", socket_type="NodeSocketFloat")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes
    gin, gout = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    build = N.new("GeometryNodeInputNamedAttribute")
    build.data_type, build.inputs["Name"].default_value = "FLOAT", "build"

    def math(op, a, b=None, clamp=False):
        n = N.new("ShaderNodeMath")
        n.operation, n.use_clamp = op, clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                ng.links.new(v, n.inputs[i])
        return n.outputs[0]

    # t: 1 not yet launched .. 0 in place
    t = math("DIVIDE", math("SUBTRACT", build.outputs["Attribute"], gin.outputs["Progress"]), FLY)
    t = math("MAXIMUM", math("MINIMUM", t, 1.0), 0.0)
    ease = math("MULTIPLY", t, t)                          # eases in to the shell
    scale = math("ADD", math("MULTIPLY", ease, FLY_FROM), 1.0)
    pos = N.new("GeometryNodeInputPosition")
    vs = N.new("ShaderNodeVectorMath")
    vs.operation = "SCALE"
    ng.links.new(pos.outputs[0], vs.inputs[0])
    ng.links.new(scale, vs.inputs["Scale"])
    setp = N.new("GeometryNodeSetPosition")
    ng.links.new(gin.outputs["Geometry"], setp.inputs["Geometry"])
    ng.links.new(vs.outputs[0], setp.inputs["Position"])
    waiting = math("GREATER_THAN", t, 0.999)
    dele = N.new("GeometryNodeDeleteGeometry")
    dele.domain = "FACE"
    ng.links.new(setp.outputs[0], dele.inputs["Geometry"])
    ng.links.new(waiting, dele.inputs["Selection"])
    ng.links.new(dele.outputs[0], gout.inputs["Geometry"])
    return ng


def globes(col):
    """A Dyson sphere under construction, floating in front of the video wall (behind her): a
    star at the centre, a faint scaffold lattice, and a shell of panels flying in and locking
    into place (see animate_globes), tilted like a planet."""
    lattice = _emission("dyson_lattice", "#4f9dff", 1.5)
    star = _emission("dyson_star", "#ffe6a8", 9.0)
    obs = []
    for k, (a, b, r, spin) in enumerate(GLOBES):
        tilt = bpy.data.objects.new(f"globe_tilt{k}", None)      # the axis tilt; the sphere spins inside
        col.objects.link(tilt)
        tilt.location = a
        tilt.rotation_euler = (0.25, 0.41, 0)
        g = bpy.data.objects.new(f"globe{k}", None)
        col.objects.link(g)
        g.parent = tilt
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r * 1.01)
        lat = bpy.context.object
        lat.name = f"globe_lattice{k}"
        for c in list(lat.users_collection):
            c.objects.unlink(lat)
        col.objects.link(lat)
        lat.parent = g
        w = lat.modifiers.new("wire", "WIREFRAME")
        w.thickness, w.use_replace = 0.003 * r / 0.36, True
        lat.data.materials.append(lattice)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=r * 0.3)
        st = bpy.context.object
        st.name = f"globe_star{k}"
        for c in list(st.users_collection):
            c.objects.unlink(st)
        col.objects.link(st)
        st.parent = g
        st.data.materials.append(star)
        me = dyson_shell(f"globe_shell{k}", r, 7 + k)
        sh = bpy.data.objects.new(f"globe_shell{k}", me)
        col.objects.link(sh)
        sh.parent = g
        pm = panel_material(k)
        me.materials.append(pm)
        mod = sh.modifiers.new("fly_in", "NODES")
        mod.node_group = fly_in_nodes(f"fly_in{k}")
        obs.append((tilt, g, pm, sh))
    return obs


# how far along each sphere's construction is at the start and end of the clip (0..1)
BUILD = [(0.25, 0.97)]
FLY = 0.07          # how long a panel takes to fly in, in build-progress units
FLY_FROM = 0.7      # it starts this many radii further out
PANEL_OPACITY = 0.7   # the panels are tinted glass: the star and the far side show through


def animate_globes(obs, n, fps):
    """Spin each sphere on its axis, let it drift slowly from its start to its end position,
    and keep adding panels."""
    for (tilt, g, pm, sh), (a, b, r, spin), (p0, p1) in zip(obs, GLOBES, BUILD):
        sock = pm.node_tree.nodes["progress"].outputs[0]
        mod = sh.modifiers["fly_in"]
        key = next(i.identifier for i in mod.node_group.interface.items_tree if i.name == "Progress")
        for f, u in ((1, 0.0), (n, 1.0)):
            tilt.location = [p + (q - p) * u for p, q in zip(a, b)]
            tilt.keyframe_insert("location", frame=f)
            g.rotation_euler.z = math.tau * spin * (n / fps / 60.0) * u
            g.keyframe_insert("rotation_euler", index=2, frame=f)
            sock.default_value = p0 + (p1 - p0) * u
            sock.keyframe_insert("default_value", frame=f)
            mod[key] = p0 + (p1 - p0) * u
            sh.keyframe_insert(f'modifiers["fly_in"]["{key}"]', frame=f)
        for ad in (tilt.animation_data, g.animation_data, pm.node_tree.animation_data, sh.animation_data):
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


def set_build(obs, u):
    """For stills: construction progress partway (u 0..1) between BUILD's start and end."""
    for (tilt, g, pm, sh), (p0, p1) in zip(obs, BUILD):
        v = p0 + (p1 - p0) * u
        pm.node_tree.nodes["progress"].outputs[0].default_value = v
        mod = sh.modifiers["fly_in"]
        mod[next(i.identifier for i in mod.node_group.interface.items_tree if i.name == "Progress")] = v


def anchor_spot():
    return (ANCHOR_SPOT[0] * P, ANCHOR_SPOT[1] * P, 0.0)


def build(sc, anchor=True):
    textures()
    col = sc.collection
    B = SL.Builder("fig", col)
    B.mats[("glass", "glass")] = glass_material()
    room = build_studio(B, col)
    gl = globes(col)
    fig = place_figure(SL.build_anchor, B, anchor_spot()) if anchor else None
    lighting(sc, anchor_spot())
    return {"room": room, "anchor": fig, "globes": gl}


def setup_render(sc, res, preview):
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_y = res
    sc.render.resolution_x = res * 16 // 9
    sc.eevee.taa_render_samples = 1 if preview else 32
    sc.eevee.use_raytracing = not preview
    sc.eevee.use_fast_gi = not preview
    sc.eevee.shadow_pool_size = "1024"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -1.0
    sc.render.image_settings.file_format = "PNG"


# The anchor shot: a classic newsreader medium shot, her on the left third (the graphics box
# sits over the right of the frame), the sign over her shoulder.
# (location, target, lens)
ANCHOR_VIEW = ((0.57, -3.4, 0.55), (0.36, 0.0, 0.55), 90)
STILLS = [
    ("anchor", *ANCHOR_VIEW),
    ("wide", (0.0, -5.2, 1.2), (0.0, 0.4, 0.75), 28),
    ("side", (-3.2, -3.4, 1.0), (0.0, 0.3, 0.6), 35),
]


def focus(cam, fstop=1.6):
    """A shallow depth of field, focused on her: the studio behind goes soft."""
    import mathutils
    d = cam.data.dof
    d.use_dof = True
    d.focus_distance = (cam.location - mathutils.Vector(anchor_spot()) - mathutils.Vector((0, 0, 0.6))).length
    d.aperture_fstop = fstop


def main():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "build", "news_stills"))
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--flat", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--clip", type=float, help="render the anchor shot as an n-second clip (globes moving)")
    A = ap.parse_args(argv)
    res = A.res or (540 if A.preview or A.flat else 1080)
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    S = build(sc)
    set_build(S["globes"], 0.3)
    setup_render(sc, res, A.preview)
    if A.flat:
        import lipsync_demo as LS
        LS.flat_look(sc)
    os.makedirs(A.out, exist_ok=True)
    if A.clip:
        n = int(A.clip * 60)
        animate_globes(S["globes"], n, 60)
        focus(camera(sc, *ANCHOR_VIEW))
        sc.frame_start, sc.frame_end, sc.render.fps = 1, n, 60
        sc.render.image_settings.file_format = "FFMPEG"
        sc.render.ffmpeg.format, sc.render.ffmpeg.codec = "MPEG4", "H264"
        sc.render.filepath = os.path.join(A.out, "anchor_clip.mp4")
        bpy.ops.render.render(animation=True)
        return
    for name, loc, tgt, lens in STILLS:
        if A.only and name not in A.only.split(","):
            continue
        cam = camera(sc, loc, tgt, lens)
        if name == "anchor":
            focus(cam)
        sc.render.filepath = os.path.join(A.out, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath)


if __name__ == "__main__":
    main()
