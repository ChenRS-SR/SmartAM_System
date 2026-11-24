import { beforeEach, expect, it, vi } from 'vitest'
import { recoverUpdatedPage } from '../router/recoverUpdatedPage'

beforeEach(() => sessionStorage.clear())
function setup() {
  let error, after
  const assign = vi.fn()
  recoverUpdatedPage({onError: fn => {error=fn}, afterEach: fn => {after=fn}, resolve: to => ({href:to.fullPath})}, {sessionStorage,location:{assign}})
  return {error,after,assign}
}
it('过期脚本重新打开原目标，保留设备参数且不循环刷新', () => {
  const {error,after,assign}=setup()
  const target={fullPath:'/slm/settings?device=slm-b44'}
  const cause=new Error('Failed to fetch dynamically imported module: /assets/Settings-old.js')
  error(cause,target)
  error(cause,target)
  expect(assign).toHaveBeenCalledExactlyOnceWith(target.fullPath)
  after(target,{},undefined)
  expect(sessionStorage.length).toBe(0)
})
it('业务错误不触发整页跳转', () => {
  const {error,assign}=setup()
  error(new Error('Invalid device'),{fullPath:'/slm/dashboard'})
  expect(assign).not.toHaveBeenCalled()
})
