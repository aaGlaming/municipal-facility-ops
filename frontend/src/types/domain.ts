export type Permission = string

export interface CurrentUser {
  subject: string
  roles: string[]
  permissions: Permission[]
  regions: string[]
  menus?: string[]
}

export interface MenuItem {
  label: string
  path: string
  group: 'core' | 'agent' | 'rag' | 'records'
  permission?: Permission
  icon: string
  description: string
}
