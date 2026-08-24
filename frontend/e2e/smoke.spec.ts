import { expect, test } from '@playwright/test';

test('creates and enters a project without external services', async ({ page, request }) => {
  const name = `E2E-${Date.now()}`;
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'LLM Wiki' })).toBeVisible();
  await page.getByRole('button', { name: '+ 新建项目' }).click();
  await page.getByPlaceholder('项目名称').fill(name);
  await page.getByRole('button', { name: '创建', exact: true }).click();
  await page.getByText(name, { exact: true }).click();
  await expect(page.getByRole('button', { name: /摄入/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /任务/ })).toBeVisible();

  const projects = await (await request.get('http://127.0.0.1:8011/api/projects')).json();
  const project = projects.data.find((item: any) => item.name === name);
  if (project) await request.delete(`http://127.0.0.1:8011/api/projects/${project.id}/data`, { data: { confirmation: name } });
});

test('keeps project schemas isolated', async ({ request }) => {
  const suffix = Date.now();
  const firstName = `Schema-A-${suffix}`;
  const secondName = `Schema-B-${suffix}`;
  const first = (await (await request.post('http://127.0.0.1:8011/api/projects', { data: { name: firstName } })).json()).data;
  const second = (await (await request.post('http://127.0.0.1:8011/api/projects', { data: { name: secondName } })).json()).data;

  try {
    const firstUrl = `http://127.0.0.1:8011/api/projects/${first.id}/schema`;
    const secondUrl = `http://127.0.0.1:8011/api/projects/${second.id}/schema`;
    const firstSchema = (await (await request.get(firstUrl)).json()).data;
    expect(firstSchema.config.language).toBe('zh-CN');

    firstSchema.config.language = 'en';
    const patched = await request.patch(firstUrl, { data: firstSchema });
    expect(patched.ok()).toBeTruthy();
    expect((await (await request.get(firstUrl)).json()).data.config.language).toBe('en');
    expect((await (await request.get(secondUrl)).json()).data.config.language).toBe('zh-CN');
  } finally {
    await request.delete(`http://127.0.0.1:8011/api/projects/${first.id}/data`, { data: { confirmation: firstName } });
    await request.delete(`http://127.0.0.1:8011/api/projects/${second.id}/data`, { data: { confirmation: secondName } });
  }
});
