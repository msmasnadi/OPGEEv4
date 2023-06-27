from opgee.error import ModelValidationError
from opgee.process import Process

class UserProcess1(Process):
    def run(self, analysis):
        # copy inputs to outputs
        for in_stream in self.inputs:
            if in_stream.is_uninitialized():
                break

            contents = in_stream.contents
            if len(contents) != 1:
                raise ModelValidationError(
                    f"UserProcess1 test streams must have only a single Content declaration; {self} inputs are {contents}")

            # If not exactly one stream that declares the same contents, raises error
            out_stream = self.find_output_stream(contents[0], raiseError=True)

            if out_stream:
                out_stream.copy_flow_rates_from(in_stream)

class UserProcess2(Process):
    def run(self, analysis):
        pass
