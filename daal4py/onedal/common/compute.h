/*******************************************************************************
* Copyright 2021 Intel Corporation
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*******************************************************************************/

#pragma once

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <numpy/arrayobject.h>

#ifdef _DPCPP_
    #include "dpctl_sycl_types.h"
    #include "dpctl_sycl_queue_manager.h"
#endif

namespace oneapi::dal::python
{
template <typename... Args>
auto compute(Args &&... args)
{
#ifdef _DPCPP_
    auto dpctl_queue = DPCTLQueueMgr_GetCurrentQueue();
    if (dpctl_queue != NULL)
    {
        cl::sycl::queue & sycl_queue = *reinterpret_cast<cl::sycl::queue *>(dpctl_queue);
        return dal::compute(sycl_queue, std::forward<Args>(args)...);
    }
    else
    {
        throw std::runtime_error("Cannot set daal context: Pointer to queue object is NULL");
    }
#else
    return dal::compute(std::forward<Args>(args)...);
#endif
}

} // namespace oneapi::dal::python
