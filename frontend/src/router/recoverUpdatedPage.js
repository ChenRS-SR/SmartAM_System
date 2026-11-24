// 部署更新后旧页面可能仍引用已删除的懒加载脚本；仅对此类错误重新打开目标页。
export function recoverUpdatedPage(router, browser = window) {
  const key = 'smartam-route-reload'
  router.onError((error, to) => {
    if (!/Failed to fetch dynamically imported module|Importing a module script failed|Failed to load module script|Unable to preload CSS|Loading chunk .* failed/i.test(error.message)) return
    if (!to) return
    const href = router.resolve(to).href
    // 同一目标最多自动刷新一次，持续网络错误不能导致无限刷新。
    if (browser.sessionStorage.getItem(key) === href) return
    browser.sessionStorage.setItem(key, href)
    browser.location.assign(href)
  })
  router.afterEach((_to, _from, failure) => {
    if (!failure) browser.sessionStorage.removeItem(key)
  })
}
