"use client";
import { ProductEditor } from './admin-add-product';
export interface AdminProductDetailsProps {
    productId: string;
    initialEdit?: boolean;
    ur?: boolean;
}
export function AdminProductDetails({ productId, initialEdit = false, ur = false }: AdminProductDetailsProps) { return <ProductEditor productId={productId} initialEdit={initialEdit} ur={ur}/>; }
