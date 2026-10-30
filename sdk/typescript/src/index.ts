export type SearchMode = "exact" | "semantic" | "hybrid";
export type Memory = {id:string; kind:"memory"; content:string; keywords:string[]; version:number; created_at:string; correction_status?:string};
export type SearchHit = {id:string; score:number; matched_keywords:Array<{query_keyword:string;stored_keyword:string;similarity:number}>};

export class VibeMemoryClient {
  constructor(private baseUrl:string, private token:string, private namespace="default") {}
  private async request<T>(path:string, init:RequestInit={}, retry=false):Promise<T> {
    const response = await fetch(new URL(path,this.baseUrl), {...init,headers:{"content-type":"application/json","authorization":`Bearer ${this.token}`,"x-vibe-memory-namespace":this.namespace,...init.headers}});
    if (response.status===429 && retry) { const delay=Math.min(Number(response.headers.get("retry-after")||1),30); await new Promise(resolve=>setTimeout(resolve,delay*1000)); return this.request<T>(path,init,false); }
    if (!response.ok) throw Object.assign(new Error(`Vibe Memory ${response.status}`),{status:response.status,body:await response.text()});
    return response.status===204 ? undefined as T : response.json() as Promise<T>;
  }
  get(id:string){ return this.request<{record:Memory}|Memory>(`/v1/records/${encodeURIComponent(id)}`); }
  search(keywords:string[],match_mode:SearchMode="hybrid"){ return this.request<{hits:SearchHit[]}>("/v1/search",{method:"POST",body:JSON.stringify({keywords,match_mode})},true); }
  create(content:string,keywords:string[],client_request_id?:string){ return this.request<Memory>("/v1/memories",{method:"POST",body:JSON.stringify({content,keywords,kind:"fact",client_request_id})},Boolean(client_request_id)); }
  correct(previous_id:string,expected_previous_version:number,replacement:{content:string;keywords:string[]},reason:string,client_request_id:string){ return this.request("/v1/corrections/memories",{method:"POST",body:JSON.stringify({previous_id,expected_previous_version,replacement:{...replacement,kind:"fact"},relation:"CORRECTS",correction_scope:"full",reason,client_request_id})},true); }
  list(limit=50,offset=0){ return this.request<{items:Memory[]}>(`/v1/records?limit=${limit}&offset=${offset}`); }
  createEntities(items:Array<Record<string,unknown>>){ return this.request("/v1/entities/batch",{method:"POST",body:JSON.stringify({items,return:"minimal",atomic:false})}); }
  contextBundle(request:Record<string,unknown>){ return this.request("/v1/context-bundle",{method:"POST",body:JSON.stringify(request)},true); }
}
