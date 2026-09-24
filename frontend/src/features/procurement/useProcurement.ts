import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "../../lib/api"
import type {
  Delivery,
  DiscrepancyReport,
  Department,
  PaginatedResponse,
  PurchaseOrder,
  PurchaseRequest,
  Quotation,
  Supplier,
  SupplierInvoice,
} from "../../types/api"

export function useDepartments() {
  return useQuery({
    queryKey: ["departments"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Department>>("/departments/")
      return data.results
    },
  })
}

export function useSuppliers() {
  return useQuery({
    queryKey: ["suppliers"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Supplier>>("/suppliers/")
      return data.results
    },
  })
}

export function usePurchaseRequests() {
  return useQuery({
    queryKey: ["purchase-requests"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<PurchaseRequest>>("/purchase-requests/")
      return data.results
    },
  })
}

export function usePurchaseRequest(id: string) {
  return useQuery({
    queryKey: ["purchase-requests", id],
    queryFn: async () => {
      const { data } = await api.get<PurchaseRequest>(`/purchase-requests/${id}/`)
      return data
    },
  })
}

interface CreatePurchaseRequestInput {
  title: string
  department: number
  items: { description: string; quantity: number; unit_price: string }[]
}

export function useCreatePurchaseRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreatePurchaseRequestInput) => {
      const { data } = await api.post<PurchaseRequest>("/purchase-requests/", input)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["purchase-requests"] }),
  })
}

function usePurchaseRequestAction(action: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload?: Record<string, string> }) => {
      const { data } = await api.post<PurchaseRequest>(`/purchase-requests/${id}/${action}/`, payload ?? {})
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["purchase-requests"] })
      queryClient.setQueryData(["purchase-requests", String(data.id)], data)
    },
  })
}

export function useSubmitPurchaseRequest() {
  return usePurchaseRequestAction("submit")
}
export function useApprovePurchaseRequest() {
  return usePurchaseRequestAction("approve")
}
export function useRejectPurchaseRequest() {
  return usePurchaseRequestAction("reject")
}

// Quotations and POs aren't filterable server-side by purchase_request, so
// we fetch the full (tenant-scoped, already small-at-this-scale) list and
// filter client-side -- same pragmatic call made elsewhere in this app.
export function useQuotationsForRequest(purchaseRequestId: number) {
  return useQuery({
    queryKey: ["quotations"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Quotation>>("/quotations/")
      return data.results
    },
    select: (quotations) => quotations.filter((q) => q.purchase_request === purchaseRequestId),
  })
}

interface CreateQuotationInput {
  purchase_request: number
  supplier: number
  amount: string
  notes?: string
}

export function useCreateQuotation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreateQuotationInput) => {
      const { data } = await api.post<Quotation>("/quotations/", input)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["quotations"] }),
  })
}

export function usePurchaseOrderForRequest(purchaseRequestId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["purchase-orders"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<PurchaseOrder>>("/purchase-orders/")
      return data.results
    },
    select: (orders) => orders.find((po) => po.purchase_request === purchaseRequestId) ?? null,
    enabled,
  })
}

interface CreatePurchaseOrderInput {
  purchase_request: number
  quotation: number
}

export function useIssuePurchaseOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreatePurchaseOrderInput) => {
      const { data } = await api.post<PurchaseOrder>("/purchase-orders/", input)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] })
      queryClient.invalidateQueries({ queryKey: ["purchase-requests"] })
    },
  })
}

export function useDiscrepancyReport(purchaseOrderId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["purchase-orders", purchaseOrderId, "discrepancy"],
    queryFn: async () => {
      const { data } = await api.get<DiscrepancyReport>(`/purchase-orders/${purchaseOrderId}/discrepancy/`)
      return data
    },
    enabled,
  })
}

interface CreateDeliveryInput {
  purchase_order: number
  is_complete: boolean
  notes?: string
}

export function useRecordDelivery() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreateDeliveryInput) => {
      const { data } = await api.post<Delivery>("/deliveries/", input)
      return data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["purchase-orders"] }),
  })
}

interface CreateSupplierInvoiceInput {
  purchase_order: number
  invoice_number?: string
  amount: string
}

export function useRecordSupplierInvoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: CreateSupplierInvoiceInput) => {
      const { data } = await api.post<SupplierInvoice>("/supplier-invoices/", input)
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] })
      queryClient.invalidateQueries({ queryKey: ["purchase-orders", variables.purchase_order, "discrepancy"] })
    },
  })
}
