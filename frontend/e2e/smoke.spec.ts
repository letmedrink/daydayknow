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
