# This file is part of the MapProxy project.
# Copyright (C) 2010 Omniscale <http://omniscale.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import division

from io import BytesIO

import pytest

from mapproxy.request.wms import WMS111MapRequest, WMS111FeatureInfoRequest
from mapproxy.test.image import tmp_image, check_format
from mapproxy.test.http import mock_httpd
from mapproxy.test.system import SysTest


@pytest.fixture(scope="module")
def config_file():
    return "formats.yaml"


def assert_file_format(filename, format):
    assert filename.check()
    check_format(filename.read_binary(), format)


class TestWMS111(SysTest):

    def setup_method(self):
        self.common_req = WMS111MapRequest(
            url="/service?", param=dict(service="WMS", version="1.1.1")
        )
        self.common_map_req = WMS111MapRequest(
            url="/service?",
            param=dict(
                service="WMS",
                version="1.1.1",
                bbox="0,0,180,80",
                width="200",
                height="200",
                layers="wms_cache",
                srs="EPSG:4326",
                format="image/png",
                styles="",
                request="GetMap",
            ),
        )
        self.common_direct_map_req = WMS111MapRequest(
            url="/service?",
            param=dict(
                service="WMS",
                version="1.1.1",
                bbox="0,0,10,10",
                width="200",
                height="200",
                layers="wms_cache",
                srs="EPSG:4326",
                format="image/png",
                styles="",
                request="GetMap",
            ),
        )
        self.common_fi_req = WMS111FeatureInfoRequest(
            url="/service?",
            param=dict(
                x="10",
                y="20",
                width="200",
                height="200",
                layers="wms_cache",
                format="image/png",
                query_layers="wms_cache",
                styles="",
                bbox="1000,400,2000,1400",
                srs="EPSG:900913",
            ),
        )
        self.expected_base_path = "/service?SERVICE=WMS&REQUEST=GetMap&HEIGHT=256" "&SRS=EPSG%3A900913&styles=&VERSION=1.1.1&WIDTH=256" "&BBOX=0.0,0.0,20037508.3428,20037508.3428"
        self.expected_direct_base_path = "/service?SERVICE=WMS&REQUEST=GetMap&HEIGHT=200" "&SRS=EPSG%3A4326&styles=&VERSION=1.1.1&WIDTH=200" "&BBOX=0.0,0.0,10.0,10.0"

    @pytest.mark.parametrize(
        "layer,source,wms_format,cache_format,req_format",
        [
            ["jpeg_cache_tiff_source", "tiffsource", "png", "jpeg", "tiff"],
            ["jpeg_cache_tiff_source", "tiffsource", "jpeg", "jpeg", "tiff"],
            ["jpeg_cache_tiff_source", "tiffsource", "tiff", "jpeg", "tiff"],
            ["jpeg_cache_tiff_source", "tiffsource", "gif", "jpeg", "tiff"],
            ["png_cache_all_source", "allsource", "png", "png", "png"],
            ["png_cache_all_source", "allsource", "jpeg", "png", "png"],
            ["jpeg_cache_png_jpeg_source", "pngjpegsource", "jpeg", "jpeg", "jpeg"],
            ["jpeg_cache_png_jpeg_source", "pngjpegsource", "png", "jpeg", "jpeg"],
        ],
    )
    def test_get_cached(
        self, app, cache_dir, layer, source, wms_format, cache_format, req_format
    ):
        with tmp_image((256, 256), format=req_format) as img:
            expected_req = (
                {
                    "path": self.expected_base_path
                    + "&layers="
                    + source
                    + "&format=image%2F"
                    + req_format
                },
                {
                    "body": img.read(),
                    "headers": {"content-type": "image/" + req_format},
                },
            )
            with mock_httpd(
                ("localhost", 42423), [expected_req], bbox_aware_query_comparator=True
            ):
                self.common_map_req.params["layers"] = layer
                self.common_map_req.params["format"] = "image/" + wms_format
                resp = app.get(self.common_map_req)
                assert resp.content_type == "image/" + wms_format
                check_format(BytesIO(resp.body), wms_format)
        assert_file_format(
            cache_dir.join(
                layer + "_EPSG900913/01/000/000/001/000/000/001." + cache_format
            ),
            cache_format,
        )

    @pytest.mark.parametrize(
        "layer,source,wms_format,req_format",
        [
            ["jpeg_cache_tiff_source", "tiffsource", "gif", "tiff"],
            ["jpeg_cache_tiff_source", "tiffsource", "jpeg", "tiff"],
            ["jpeg_cache_tiff_source", "tiffsource", "png", "tiff"],
            ["png_cache_all_source", "allsource", "gif", "gif"],
            ["png_cache_all_source", "allsource", "png", "png"],
            ["png_cache_all_source", "allsource", "tiff", "tiff"],
            ["jpeg_cache_png_jpeg_source", "pngjpegsource", "jpeg", "jpeg"],
            ["jpeg_cache_png_jpeg_source", "pngjpegsource", "png", "png"],
            ["jpeg_cache_png_jpeg_source", "pngjpegsource", "tiff", "png"],
            ["jpeg_cache_png_jpeg_source", "pngjpegsource", "gif", "png"],
        ],
    )
    def test_get_direct(self, app, layer, source, wms_format, req_format):
        with tmp_image((256, 256), format=req_format) as img:
            expected_req = (
                {
                    "path": self.expected_direct_base_path
                    + "&layers="
                    + source
                    + "&format=image%2F"
                    + req_format
                },
                {
                    "body": img.read(),
                    "headers": {"content-type": "image/" + req_format},
                },
            )
            with mock_httpd(
                ("localhost", 42423), [expected_req], bbox_aware_query_comparator=True
            ):
                self.common_direct_map_req.params["layers"] = layer
                self.common_direct_map_req.params["format"] = "image/" + wms_format
                resp = app.get(self.common_direct_map_req)
                assert resp.content_type == "image/" + wms_format
                check_format(BytesIO(resp.body), wms_format)


class TestTMS(SysTest):

    def setup_method(self):
        self.expected_base_path = "/service?SERVICE=WMS&REQUEST=GetMap&HEIGHT=256" "&SRS=EPSG%3A900913&styles=&VERSION=1.1.1&WIDTH=256" "&BBOX=0.0,0.0,20037508.3428,20037508.3428"
        self.expected_direct_base_path = "/service?SERVICE=WMS&REQUEST=GetMap&HEIGHT=200" "&SRS=EPSG%3A4326&styles=&VERSION=1.1.1&WIDTH=200" "&BBOX=0.0,0.0,10.0,10.0"

    @pytest.mark.parametrize(
        "layer,source,tms_format,cache_format,req_format",
        [
            ["jpeg_cache_tiff_source", "tiffsource", "jpeg", "jpeg", "tiff"],
            ["png_cache_all_source", "allsource", "png", "png", "png"],
            ["jpeg_cache_png_jpeg_source", "pngjpegsource", "jpeg", "jpeg", "jpeg"],
        ],
    )
    def test_get_cached(
        self, app, cache_dir, layer, source, tms_format, cache_format, req_format
    ):
        with tmp_image((256, 256), format=req_format) as img:
            expected_req = (
                {
                    "path": self.expected_base_path
                    + "&layers="
                    + source
                    + "&format=image%2F"
                    + req_format
                },
                {
                    "body": img.read(),
                    "headers": {"content-type": "image/" + req_format},
                },
            )
            with mock_httpd(
                ("localhost", 42423), [expected_req], bbox_aware_query_comparator=True
            ):
                resp = app.get("/tms/1.0.0/%s/0/1/1.%s" % (layer, tms_format))
                assert resp.content_type == "image/" + tms_format
                # check_format(BytesIO(resp.body), tms_format)
        assert_file_format(
            cache_dir.join(
                layer + "_EPSG900913/01/000/000/001/000/000/001." + cache_format
            ),
            cache_format,
        )
