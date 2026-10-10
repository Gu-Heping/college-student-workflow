# Reader Audit: Teaching Counterexamples

Use these synthetic cases to calibrate AI review, not as prose to paste into a course page. A script cannot decide whether a student can learn from a page. The main agent reads the actual page and follows its actual calculations.

## Operations Without Definitions

Weak: "Row-reduce to echelon form and read the rank."

Repair direction: define the permitted row operations and the first nonzero entry, demonstrate eliminating a lower entry with an explicit small matrix, then explain which nonzero rows determine rank. Revisit the actual exam question and show its elimination steps. Ask whether the beginner could carry out the operation rather than merely recognize its name.

## Methods Without Teaching Examples

Weak: "Use an inverse, elimination, or an adjugate as appropriate."

Repair direction: explain the condition selecting each method, allocate real problems to teach those choices, then show a complete worked solution. Keep independent real problems to test the same choices. Do not manufacture another exam question to fill a missing slot.

## Duplicate Tests And Exhausted Pools

Weak: all available questions are worked examples, followed by the same questions under self-tests with a different solution.

Repair direction: reserve disjoint question identities before writing. Move some examples into tests; if independent variants remain unavailable, describe the uncovered methods and reduce counts. A conceptual calculation may demonstrate an operation but cannot masquerade as a past-paper test.

## Links Instead Of Concepts

Weak: "See textbook section 2.3 for inverse matrices."

Repair direction: read that section, explain what multiplying by the inverse does, why multiplication direction matters, and when the inverse exists. Keep the precise locator in the source record/appendix; the student should not have to leave the page to understand the basic operation.

## Speed Cards Before Learning

Weak: a first screen of compressed identities with no explanation of the symbols.

Repair direction: first show the page's purpose and two links. Beginners enter concepts and a concrete calculation; returning students go straight to the speed card. Do not repeat generic prerequisites on every page.

## Conflicting Routes

Weak: the guide starts with type T1, while the entry recommends T7 which silently needs T3.

Repair direction: trace the first actual dependency, explain it locally and link its lesson, then synchronize the entry, guide and speed-card order. Do not rename stable type IDs simply to change the learning sequence.

## Stale Audit And Numerical Overclaims

Weak: a last month's audit approves this week's rewritten answers; checking three matrices is called a proof for all matrices.

Repair direction: read the revised files and update this round's audit with paths, current revisions, concrete corrections and remaining risks; keep the previous round as history. Label exact calculations, numerical spot checks and general proofs separately. Resolve OCR gaps from source evidence, not by guessing a problem that matches the answer.

## Summaries Before Source Analysis

Weak: the guide and formula card are declared ready because every link works, although their problem pages are still stubs. Later analysis reveals that a turning-point condition was confused with a contact-loss condition.

Repair direction: read the original problem, identify the physical event and derive its condition before writing the shortcut. Correct both the worked solution and every summary carrying the old claim. Mark a partial route as partial; reachable files do not make an exam-ready pack.

## Missed Lectures Are Not A New Deliverable

Weak: a request to finish problem-led revision material becomes a separate lecture-note series, or the agent refuses to continue until the student does closed-book exercises. Submitted homework is treated as proof of mastery.

Repair direction: keep writing the requested material. Explain the symbols and necessary operation where the first real problem needs them, then demonstrate a guided solution. Offer an independent test without making the student's attempt a prerequisite for finishing the page. Separate notes are appropriate when requested, not simply because the student missed class.

## A Successful Edit With A Broken Join

Weak: a table-row replacement matches only through `T5 → T`, inserts complete new rows, and leaves the old suffix `6 → ... |` attached to the last new row. Links still resolve, so the agent reports success.

Repair direction: read and replace the complete row with distinguishing context. Read the saved table and neighboring paragraphs after the edit, including its final cells. Repair the join locally; neither the tool's match result nor a link checker proves the resulting sentence is intact.

## A Correct Limit Does Not Prove The Given Angle

Weak: a solution reduces to the textbook answer at a known angle, so the agent claims that an unclear scanned angle was transcribed correctly. It asks the student to check every uncertainty despite having access to the original PDF and relevant course figures.

Repair direction: separate source transcription from mathematical consistency. Inspect the original page and local crop when vision is available; compare independent course evidence. If the source remains unreadable or vision is unavailable, state that limitation and ask about the specific consequential detail. A valid derivation does not settle an illegible given, and AI source checking is not human verification.

## Draft Reports Instead Of Reader Review

Weak: a subagent reports a long, complete page; the coordinator reads only its opening and link report. The task guessed the wrong relative paths and silently substituted textbook exercises for required past-paper tests.

Repair direction: give the writer actual source and output locations and reserved question identities. Read the saved complete example, independent test answer and source labels. Fix paths and teaching gaps locally; when independent past-paper questions are insufficient, report the gap rather than disguising supplementary exercises as exam questions.

## Acceptance Exercise

### A Concrete Teaching Repair

This small demonstration is synthetic, not a past-paper example or a self-test.

**用途**：理解“消掉一行”到底做了什么。零基础先读下面的操作；考前只需回看末尾的判断。

一行就是矩阵中横着排列的一组数，$R_1$ 表示第一行，$R_2$ 表示第二行。把一行的倍数加到另一行是允许的初等行变换：它不会改变各行能生成的线性组合范围。秩就是其中独立方向的数量；变成阶梯形后，可以数非零行。

先看这个矩阵：

$$
A=\begin{pmatrix}1&2\\2&4\end{pmatrix}.
$$

第二行正好是第一行的两倍，所以不提供新的方向。用 $R_2\leftarrow R_2-2R_1$ 消掉它：第一个数算 $2-2\times1=0$，第二个数算 $4-2\times2=0$，得到

$$
\begin{pmatrix}1&2\\0&0\end{pmatrix}.
$$

现在只有一行非零，因此秩为 $1$。检查：第一行非零，第二行确实是它的倍数，结论一致。这里是精确计算，不是“随机抽验，所以所有矩阵都成立”。

**迁移**：回到真实题池，选择需要换行或含参数的题教下一种判断，再保留另一道独立真题做自测；不能把这个演示冒充往年卷。**速查**：行阶梯形中数非零行；不要数消元前的非零行。

AI 审读重点：定义了行操作记号、给出逐项计算、解释了为何可变换、写出具体答案和检查，并区分演示与真题。是否足以支撑某门课的完整题型页，仍要读其实际例题和课程来源才能判断。

Use an ordinary request: "Improve this type-analysis page so someone who missed the lectures can learn to solve the problems." Do not add a hidden checklist to the user's prompt. Observe whether the agent reads relevant sources, supplies executable operations, allocates disjoint real problems, revises after read-back and records concrete current findings. Mechanical success is reported separately from AI review; both remain unverified by a human.
