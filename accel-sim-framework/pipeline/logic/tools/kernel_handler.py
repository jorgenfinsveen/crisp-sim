#!/usr/bin/env python3

class KernelHandler:
    RENDER_KERNEL_PREFIX = "MESA"

    def __init__(self, kernels: list[str]):
        self.kernels = kernels
        self.render_kernels: list[str] = []
        self.compute_kernels: list[str] = []
        self.__sort_kernels()

    #Sort all the kernels into a render kernel list and a compute kernel list
    def __sort_kernels(self):
        for kernel in self.kernels:
            if self.is_render_kernel(kernel):
                self.render_kernels.append(kernel)
            else:
                self.compute_kernels.append(kernel)

    #Checks if a kernel contains the prefix MEAS
    def __string_contains_meas(self, kernel_name: str) -> bool:
        return self.RENDER_KERNEL_PREFIX in kernel_name

    #Returns all render kernel as a list
    def get_render_kernels(self) -> list[str]:
        return self.render_kernels

    #Returns all compute kernel as a list
    def get_compute_kernels(self) -> list[str]:
        return self.compute_kernels

    #Return all kernels
    def get_all_kernels(self) -> list[str]:
        return self.kernels

    #Return the number of render kernels
    def get_number_of_render_kernels(self) -> int:
        return len(self.render_kernels)

    #Return the number of compute kernels
    def get_number_of_compute_kernels(self) -> int:
        return len(self.compute_kernels)

    #Return the number of kernels
    def get_number_of_kernels(self) -> int:
        return len(self.kernels)

    #Returns true if a kernel is a render kernel, false otherwise
    def is_render_kernel(self, kernel_name: str) -> bool:
        return self.__string_contains_meas(kernel_name)

    #Return true if kernel is a compute kernel, false otherwise
    def is_compute_kernel(self, kernel_name: str) -> bool:
        return not self.__string_contains_meas(kernel_name)