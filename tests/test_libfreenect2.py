# coding: utf-8

import numpy as np

from nose.tools import raises
from nose.plugins.attrib import attr

from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame, FrameMap


def test_frame():
    frame = Frame(512, 424, 4)
    assert frame.width == 512
    assert frame.height == 424
    assert frame.bytes_per_pixel == 4
    assert frame.exposure == 0
    assert frame.gain == 0
    assert frame.gamma == 0


def test_enumerateDevices():
    fn = Freenect2()
    fn.enumerateDevices()


@attr('require_device')
def test_openDefaultDevice():
    fn = Freenect2()

    num_devices = fn.enumerateDevices()
    assert num_devices > 0

    device = fn.openDefaultDevice()

    device.stop()
    device.close()


@attr('require_device')
def test_sync_multi_frame():
    fn = Freenect2()

    num_devices = fn.enumerateDevices()
    assert num_devices > 0

    serial = fn.getDefaultDeviceSerialNumber()
    assert serial == fn.getDeviceSerialNumber(0)

    device = fn.openDevice(serial)

    assert fn.getDefaultDeviceSerialNumber() == device.getSerialNumber()
    device.getFirmwareVersion()

    listener = SyncMultiFrameListener(
        FrameType.Color | FrameType.Ir | FrameType.Depth)

    # Register listeners
    device.setColorFrameListener(listener)
    device.setIrAndDepthFrameListener(listener)

    device.start()

    # Registration
    registration = Registration(device.getIrCameraParams(),
                                device.getColorCameraParams())
    undistorted = Frame(512, 424, 4)
    registered = Frame(512, 424, 4)

    # optional parameters for registration
    bigdepth = Frame(1920, 1082, 4)
    color_depth_map = np.zeros((424, 512), np.int32)

    # test if we can get two frames at least
    frames = listener.waitForNewFrame()
    listener.release(frames)

    # frames as a first argment also should work
    frames = FrameMap()
    listener.waitForNewFrame(frames)

    color = frames[FrameType.Color]
    ir = frames[FrameType.Ir]
    depth = frames[FrameType.Depth]

    for frame in [ir, depth]:
        assert frame.exposure == 0
        assert frame.gain == 0
        assert frame.gamma == 0

    for frame in [color]:
        assert frame.exposure > 0
        assert frame.gain > 0
        assert frame.gamma > 0

    registration.apply(color, depth, undistorted, registered)

    # with optinal parameters
    registration.apply(color, depth, undistorted, registered,
                       bigdepth=bigdepth,
                       color_depth_map=color_depth_map.ravel())

    assert color.width == 1920
    assert color.height == 1080
    assert color.bytes_per_pixel == 4

    assert ir.width == 512
    assert ir.height == 424
    assert ir.bytes_per_pixel == 4

    assert depth.width == 512
    assert depth.height == 424
    assert depth.bytes_per_pixel == 4

    assert color.asarray().shape == (color.height, color.width, 4)
    assert ir.asarray().shape == (ir.height, ir.width)
    assert depth.astype(np.float32).shape == (depth.height, depth.width)

    listener.release(frames)

    def __test_cannot_determine_type_of_frame(frame):
        frame.asarray()

    for frame in [registered, undistorted]:
        yield raises(ValueError)(__test_cannot_determine_type_of_frame), frame

    device.stop()
    device.close()
