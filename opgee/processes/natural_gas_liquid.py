#
# NGL class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class NGL(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()

    def run(self, analysis):
        self.print_running_msg()
