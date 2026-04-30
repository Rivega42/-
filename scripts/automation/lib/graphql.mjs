/**
 * Общие GraphQL-запросы к GitHub Projects v2 и Sub-issues API.
 * Используется всеми скриптами автоматизации.
 *
 * Переменные окружения:
 *   PROJECT_TOKEN — PAT с правами repo + project + read:org
 *   PROJECT_NUMBER — номер проекта в организации/репо
 *   PROJECT_OWNER — owner организации или пользователя
 */

/**
 * Получает ID проекта по номеру.
 */
export async function getProjectId(github, owner, projectNumber) {
  const result = await github.graphql(
    `query($owner: String!, $number: Int!) {
      organization(login: $owner) {
        projectV2(number: $number) { id }
      }
      user(login: $owner) {
        projectV2(number: $number) { id }
      }
    }`,
    { owner, number: parseInt(projectNumber, 10) }
  );
  return result.organization?.projectV2?.id || result.user?.projectV2?.id;
}

/**
 * Получает все кастомные поля проекта с их option-ID.
 * Возвращает map { fieldName: { id, options: { optionName: optionId } } }.
 */
export async function getProjectFields(github, projectId) {
  const result = await github.graphql(
    `query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2FieldCommon { id name dataType }
              ... on ProjectV2SingleSelectField {
                id name dataType
                options { id name }
              }
              ... on ProjectV2IterationField {
                id name dataType
                configuration {
                  iterations { id title startDate duration }
                }
              }
            }
          }
        }
      }
    }`,
    { projectId }
  );
  const fields = {};
  for (const f of result.node.fields.nodes) {
    if (!f) continue;
    fields[f.name] = {
      id: f.id,
      dataType: f.dataType,
      options: f.options ? Object.fromEntries(f.options.map(o => [o.name, o.id])) : undefined,
      iterations: f.configuration?.iterations,
    };
  }
  return fields;
}

/**
 * Находит ProjectV2Item по issue/PR node_id.
 * Если в проекте нет — возвращает null.
 */
export async function findProjectItem(github, projectId, contentNodeId) {
  const result = await github.graphql(
    `query($projectId: ID!, $contentId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: 100) {
            nodes {
              id
              content {
                ... on Issue { id }
                ... on PullRequest { id }
              }
            }
          }
        }
      }
    }`,
    { projectId, contentId: contentNodeId }
  );
  const item = result.node.items.nodes.find(i => i.content?.id === contentNodeId);
  return item?.id || null;
}

/**
 * Добавляет issue/PR в проект.
 */
export async function addItemToProject(github, projectId, contentNodeId) {
  const result = await github.graphql(
    `mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
        item { id }
      }
    }`,
    { projectId, contentId: contentNodeId }
  );
  return result.addProjectV2ItemById.item.id;
}

/**
 * Устанавливает single-select поле.
 */
export async function setSingleSelect(github, projectId, itemId, fieldId, optionId) {
  await github.graphql(
    `mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
        value: { singleSelectOptionId: $optionId }
      }) { projectV2Item { id } }
    }`,
    { projectId, itemId, fieldId, optionId }
  );
}

/**
 * Устанавливает text-поле.
 */
export async function setText(github, projectId, itemId, fieldId, text) {
  await github.graphql(
    `mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $text: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
        value: { text: $text }
      }) { projectV2Item { id } }
    }`,
    { projectId, itemId, fieldId, text }
  );
}

/**
 * Устанавливает number-поле.
 */
export async function setNumber(github, projectId, itemId, fieldId, num) {
  await github.graphql(
    `mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $num: Float!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
        value: { number: $num }
      }) { projectV2Item { id } }
    }`,
    { projectId, itemId, fieldId, num }
  );
}

/**
 * Устанавливает date-поле (формат YYYY-MM-DD).
 */
export async function setDate(github, projectId, itemId, fieldId, dateStr) {
  await github.graphql(
    `mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $date: Date!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId, itemId: $itemId, fieldId: $fieldId,
        value: { date: $date }
      }) { projectV2Item { id } }
    }`,
    { projectId, itemId, fieldId, date: dateStr }
  );
}

/**
 * Получает sub-issues родителя через native API.
 * Использует REST endpoint /issues/:number/sub_issues.
 */
export async function getSubIssues(github, owner, repo, issueNumber) {
  try {
    const { data } = await github.rest.request(
      'GET /repos/{owner}/{repo}/issues/{issue_number}/sub_issues',
      { owner, repo, issue_number: issueNumber }
    );
    return data;
  } catch (e) {
    if (e.status === 404) return [];
    throw e;
  }
}

/**
 * Получает родителя issue через native sub-issues API.
 */
export async function getParentIssue(github, owner, repo, issueNumber) {
  try {
    const { data } = await github.rest.request(
      'GET /repos/{owner}/{repo}/issues/{issue_number}/parent',
      { owner, repo, issue_number: issueNumber }
    );
    return data;
  } catch (e) {
    if (e.status === 404) return null;
    throw e;
  }
}

/**
 * Связывает issue как sub-issue к parent.
 */
export async function addSubIssue(github, owner, repo, parentNumber, childIssueId) {
  await github.rest.request(
    'POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues',
    { owner, repo, issue_number: parentNumber, sub_issue_id: childIssueId }
  );
}

/**
 * Получает все open issues с указанным лейблом.
 */
export async function getIssuesByLabel(github, owner, repo, label, state = 'open') {
  const issues = [];
  for await (const { data } of github.paginate.iterator(github.rest.issues.listForRepo, {
    owner, repo, labels: label, state, per_page: 100,
  })) {
    issues.push(...data);
  }
  return issues.filter(i => !i.pull_request);
}

/**
 * Постит комментарий в issue.
 */
export async function commentOnIssue(github, owner, repo, issueNumber, body) {
  await github.rest.issues.createComment({ owner, repo, issue_number: issueNumber, body });
}

/**
 * Добавляет лейбл к issue (idempotent).
 */
export async function addLabel(github, owner, repo, issueNumber, label) {
  await github.rest.issues.addLabels({ owner, repo, issue_number: issueNumber, labels: [label] });
}

/**
 * Снимает лейбл с issue (silent если нет).
 */
export async function removeLabel(github, owner, repo, issueNumber, label) {
  try {
    await github.rest.issues.removeLabel({ owner, repo, issue_number: issueNumber, name: label });
  } catch (e) {
    if (e.status !== 404) throw e;
  }
}
